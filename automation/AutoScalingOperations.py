import boto3


class AutoScalingOperations:
	# this class deals with autoscaling operations
	as_client = boto3.client('autoscaling')
	dynamodb_client = boto3.client('dynamodb')
	
	def __init__(self, asg_name_list, table_name):
		self.asg_name_list  = asg_name_list
		self.table_name = table_name
		
	def setDesiredCountToZero(self):
		print "Getting Current desired Values and Min Values from Auto Scaling Service:"
		print self.getDesiredCountFromAS()
		
		self.putDesiredCountsToDB()
		
		
		for asg_name in self.asg_name_list:
			print ("Setting desired count and min count for ASG: %s to: %d and %d" % (asg_name, 0, 0))
			# response = self.as_client.set_desired_capacity(
			# 	AutoScalingGroupName=asg_name,
			# 	DesiredCapacity=0,
			# 	HonorCooldown=False
			# )
			response = self.as_client.update_auto_scaling_group(
				AutoScalingGroupName=asg_name,
				MinSize=0,
				DesiredCapacity=0
			)
			print ("Debug: %s" % (str(response)))
			
		print "Getting Current desired Values and Min Values from Auto Scaling Service:"
		print self.getDesiredCountFromAS()
		
	def putDesiredCountsToDB(self):
		#item_to_put = {'asg_name': {'S': 'dummy_asg_name'}, 'desired_count': {'N': '2'}}
		
		desired_counts = self.getDesiredCountFromAS()[0]
		min_counts = self.getDesiredCountFromAS()[1]
		print "Putting current Desired Counts to DB."
		for asg_name in self.asg_name_list:
			item_to_put  = {'asg_name': {'S': asg_name},
			                'desired_count': { 'N': str(desired_counts[asg_name])},
			                'min_count': {'N': str(min_counts[asg_name])}
			                }
			response = self.dynamodb_client.put_item(TableName = self.table_name,
			                                         Item=item_to_put
			                                         )
			
		
		
		
	def getDesiredCountFromAS(self):
		# reads the desired count and min count from auto-scaling service and not from db
		# this should only be called before setting the desired to 0
		# this should not be called while restoring the desired count
		
		# returns two dicts with asg_name: desired_count pairs and asg_name: min_count
		
		
		
		desired_counts = {}
		min_counts = {}
		response = self.as_client.describe_auto_scaling_groups(
			AutoScalingGroupNames=self.asg_name_list
		)
		for asg in response['AutoScalingGroups']:
			desired_counts[asg['AutoScalingGroupName']] = asg['DesiredCapacity']
			min_counts[asg['AutoScalingGroupName']] = asg['MinSize']
		
		return desired_counts, min_counts
	
	def restoreDesiredCounts(self):
		
		print "Getting desired Counts and min counts from DB"
		for asg_name in self.asg_name_list:
			response = self.dynamodb_client.get_item(TableName=self.table_name,Key={'asg_name': {'S': asg_name}})
			desired_count = int(response['Item']['desired_count']['N'])
			min_count = int(response['Item']['min_count']['N'])
			
			print ("Setting desired count and min count for ASG: %s to: %d and %d" % (asg_name, desired_count, min_count))
			
			# response = self.as_client.set_desired_capacity(
			# 	AutoScalingGroupName=asg_name,
			# 	DesiredCapacity=desired_count,
			# 	HonorCooldown=False
			# )
			
			response = self.as_client.update_auto_scaling_group(
				AutoScalingGroupName=asg_name,
				MinSize=min_count,
				DesiredCapacity=desired_count
			)
			
		
		print "Getting Desired Values and Min Values from Auto Scaling Service:"
		print self.getDesiredCountFromAS()
		
		
		
		