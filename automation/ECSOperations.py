import boto3
import json

class ECSOperations:
	
	ecs_client = boto3.client('ecs')
	aas_client = boto3.client('application-autoscaling')
	dynamodb_client = boto3.client('dynamodb')
	
	def __init__(self, clusters, table_name, ):
		self.clusters = clusters # lits of all clusters to affect
		self.table_name = table_name
		
	def getServicesList(self, cluster):
		# input cluster string
		# output list containins services
		response = self.ecs_client.list_services(
			cluster=cluster
		)
		
		
		services_list =[]
		for i in range (len(response['serviceArns'])):
			services_list.append(str(response['serviceArns'][i]).split("/")[1])
		
		#print "servics in cluster: "+cluster
		#print services_list
		return services_list
		
	def getServicesDesiredCounts(self, cluster, services_list):
		# output dictonaries containing "service: desried count " pairs and service: min count "
		
		response = self.ecs_client.describe_services(
			cluster=cluster,
			services=services_list
		)
		
		
		services_desired_counts = {}
		
		for i in range (len(response['services'])):
			services_desired_counts[response['services'][i]['serviceName']] = int(response['services'][i]['desiredCount'])
			
			
		
		non_unicode_desired_dict = {str(k): v for (k, v) in services_desired_counts.items()}
		
		ecs_scalable_resources_list = []
		for service in services_list:
			ecs_scalable_resources_list.append('service/' + cluster + '/' + service)
		
		response = self.aas_client.describe_scalable_targets(
			ServiceNamespace='ecs',
			ResourceIds=ecs_scalable_resources_list,
			ScalableDimension='ecs:service:DesiredCount',
		)
		services_min_counts = {}
		
		for scalable_targets in response['ScalableTargets']:
			services_min_counts[scalable_targets['ResourceId'].split("/")[2]] = int(scalable_targets['MinCapacity'])
		
		non_unicode_min_dict = {str(k): v for (k, v) in services_min_counts.items()}
		return non_unicode_desired_dict, non_unicode_min_dict
	
	def putDesiredCountsToDB(self, cluster, services_list):
		print ("services in cluster '%s': %s" % (cluster, str(services_list)))
		item_to_put={}
		item_to_put['cluster_name']={'S' : cluster}
		item_to_put = dict (item_to_put, **{"desired_counts" : { 'S' : str(self.getServicesDesiredCounts(cluster, services_list)[0])},
		                                    "min_counts": {
			                                    'S': str(self.getServicesDesiredCounts(cluster, services_list)[1])}})
		
		print "Putting Service count in DB:"
		print item_to_put
		
		response = self.dynamodb_client.put_item(
			TableName=self.table_name,
			Item=item_to_put
		)
		
	def setDesiredCountsToZero(self):
		# takes in a list of services and cluster name
		# sets the desired count to 0 for all the services.
		
		for cluster in self.clusters:
			services_list = self.getServicesList(cluster)
			
			self.putDesiredCountsToDB(cluster, services_list)
			
			
			print "setting desired count and min count for all services in cluster: "+cluster+" to zero"
			for service in services_list:
				response = self.ecs_client.update_service(
					cluster=cluster,
					service=service,
					desiredCount=0,
				)
				
				response = self.aas_client.register_scalable_target(
					ServiceNamespace='ecs',
					ResourceId='service/'+cluster+'/'+service,
					ScalableDimension='ecs:service:DesiredCount',
					MinCapacity=0
				)
			print ("Desired count and min count from ECS for cluster '%s' : %s and %s" % (cluster, str(self.getServicesDesiredCounts(cluster, services_list)[0],
			                                                                                           str(self.getServicesDesiredCounts(cluster, services_list)[1]))))
		
		
			
	
	def restoreDesiredCountsFromDB(self):
		# for each clustr in clusters, retrieve the service and counts and set it back on

		
		for cluster in self.clusters:
			print ("restoring min  and desired count for services in cluster '%s'" % (cluster))
			response = self.dynamodb_client.get_item(TableName=self.table_name,Key={'cluster_name': {'S': cluster}})
			services_and_desired_counts = eval(response['Item']['desired_counts']['S'])
			services_and_min_counts = eval(response['Item']['min_counts']['S'])
			
			for service, min_count in services_and_min_counts.iteritems():
				response = self.aas_client.register_scalable_target(
					ServiceNamespace='ecs',
					ResourceId='service/' + cluster + '/' + service,
					ScalableDimension='ecs:service:DesiredCount',
					MinCapacity=min_count
				)
				
				print ("Setting min count for service '%s' to %d" % (service, int(min_count)))

		
			for service, desired_count in services_and_desired_counts.iteritems():
				
				response = self.ecs_client.update_service(
					cluster=cluster,
					service=service,
					desiredCount=desired_count,
				)
				
				print ("Setting desired count for service '%s' to %d" % (service, int(desired_count)))
			
			
			
