import boto3
import json

class ECSOperations:
	
	ecs_client = boto3.client('ecs')
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
		# output dictonary containing "service: desried count " pairs
		
		response = self.ecs_client.describe_services(
			cluster=cluster,
			services=services_list
		)
		
		services_desired_counts = {}
		for i in range (len(response['services'])):
			services_desired_counts[response['services'][i]['serviceName']] = int(response['services'][i]['desiredCount'])
		
		non_unicode_dict = {str(k): v for (k, v) in services_desired_counts.items()}
		
		#print non_unicode_dict
		return non_unicode_dict
	
	def putDesiredCountsToDB(self, cluster, services_list):
		print ("services in cluster '%s': %s" % (cluster, str(services_list)))
		item_to_put={}
		item_to_put['cluster_name']={'S' : cluster}
		item_to_put = dict (item_to_put, **{"desired_counts" : { 'S' : str(self.getServicesDesiredCounts(cluster, services_list))}})
		
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
			
			
			print "setting desired count for all services in cluster: "+cluster+" to zero"
			for service in services_list:
				response = self.ecs_client.update_service(
					cluster=cluster,
					service=service,
					desiredCount=0,
				)
			print ("Desired count from ECS for cluster '%s' : %s" % (cluster, str(self.getServicesDesiredCounts(cluster, services_list))))
		
		
			
	
	def restoreDesiredCountsFromDB(self):
		# for each clustr in clusters, retrieve the service and counts and set it back on

		
		for cluster in self.clusters:
			print ("restoring service count for cluster '%s'" % (cluster))
			response = self.dynamodb_client.get_item(TableName=self.table_name,Key={'cluster_name': {'S': cluster}})
			services_and_desired_counts = eval(response['Item']['desired_counts']['S'])
			
		
			for service, desired_count in services_and_desired_counts.iteritems():
				
				response = self.ecs_client.update_service(
					cluster=cluster,
					service=service,
					desiredCount=desired_count,
				)
				
				print ("Setting desired count for service '%s' to %d" % (service, int(desired_count)))
			
			
			
