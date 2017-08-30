from automation import *
import re

# Start Configurable variables
ecs_clusters=['stage-nginx','stage-frontend', 'stage-worker-1', 'stage-worker-2'] # for multiple clusters: example [ 'cluster1', 'cluster2' ]
asg_name_list = ['stage-nginx','stage-frontend', 'stage-worker-1', 'stage-worker-2']


# dynamodb
ecs_dynamo_db_table_name="automated-stop-start-ecs"
asg_dynamo_db_table_name="automated-stop-start-asg"
info_dynamo_db_table_name = "automated-stop-start-info"
ignore_next_trigger_key = "ignore_this_many_upcoming_trggers"
environment_state_key="state"
#sns
sns_topic_arn = "arn:aws:sns:us-west-2:826188132410:automated-stop-start"
suppress_notifications=False # if this is set to true, notification emails will not be sent - FOR DEBUGGING

#RDS
db_instance_id = "stage-postgres-encrypted"
db_instance_snapshot_id = "stage-postgres-encrypted-before-stop"


environment_name = "Stage Environment"

# to stop ec2 based on tags, use the variable below
tags=[{'auto-stop-start': '1'}]  # For multiple tags keys and values : Exampple: [{'auto-stop-start':'1'}, {'user':'ubuntu'}]


jenkins_job_build_with_parameter_url = "http://jenkins.qa.reachify.io/job/automated-stop-start-operations/build?delay=0sec"
# End Configurable variables

event_global = None
def lambda_handler(event, context):
	stubCaller()
	global event_global
	event_global = dict(event)
	
	ec2operations = EC2Operations(tags)
	ecsoperations = ECSOperations(ecs_clusters, ecs_dynamo_db_table_name)
	asoperations = AutoScalingOperations(asg_name_list, asg_dynamo_db_table_name)
	snsoperations = SNSOperations(sns_topic_arn, suppress_notifications)
	dynamodboperations = DynamoDBOperations(info_dynamo_db_table_name)
	rdsoperations = RDSOperations(db_instance_id, db_instance_snapshot_id)
	
	
	if event['action'] == "manual-switch-on":
		switchOn(ecsoperations, asoperations, snsoperations, ec2operations, rdsoperations, dynamodboperations, is_triggered_manually=True)
		return "called switchOn()"
	
	elif event['action'] == "manual-switch-off":
		switchOff(ecsoperations, asoperations, snsoperations, ec2operations, rdsoperations, dynamodboperations, is_triggered_manually=True)
		return "called switchOff()"
	
	elif event['action'] == "ignore-next-trigger":
		pushIgnoreNextTrigger(dynamodboperations)
		#notify about ignore-next-trigger
		
		snsoperations.pushNotification(str(getIgnoreNextTrigger(dynamodboperations))+ " Upcoming Scheduled Event(s) Will Be Ignored",
		                               "Hi,\n\n"
		                               "This mail is in regards to automated shutting down and starting of "+environment_name+"\n\n"
		                               "Upcoming Event(s) have been ignored by Stage Jenkins user: "+ event ['user'])
		return "called pushIgnoreNextTrigger"
	
	elif event['action'] == "get-ignore-next-trigger":
		print getIgnoreNextTrigger(dynamodboperations)
		return "called getIgnoreNextTrigger"
	
	
	## VERY IMPORTANT ##
	# all the scheduled action (which are being triggered through cloudwatch event)
	# should have the term "schedule" in their value
	# example: {"action" : "schedule-something" } <-- This is right
	# example: {"action" : "act-on-something" }   <-- THis is wrong
	
	pattern  = re.compile(".*schedule.*")
	
	
	if getIgnoreNextTrigger(dynamodboperations) is 0:
		# no trigger is set to skip
		# execute scheduled triggers
		if event['action'] == "scheduled-switch-on" :
		   switchOn(ecsoperations, asoperations, snsoperations, ec2operations, rdsoperations, dynamodboperations)
		   return "called switchOn()"
		
		elif event['action'] == "scheduled-switch-off":
			switchOff(ecsoperations, asoperations, snsoperations, ec2operations, rdsoperations, dynamodboperations)
			return "called switchOff()"
		
		elif event['action'] == "pre-schedule-notify-off": # notify about scheduled shutdown
			snsoperations.pushNotification(environment_name+ " Is Going To Be Down In Next One Hour",
										   "Hi,\n\n"
										   "You can use "+ jenkins_job_build_with_parameter_url +" to override the scheduled event")
			
		elif event['action'] == "pre-schedule-notify-on": # notify about scheduled poweron
			snsoperations.pushNotification(environment_name + " Is Going To Be Up In Next One Hour",
										   "Hi,\n\n"
										   "You can use "+jenkins_job_build_with_parameter_url+" to override the scheduled event")
	elif pattern.match(str(event['action'])) is not None:
		print "ignore trigger is set to more than 0"
		print "decreasing the value by 1"
		popIgnoreNextTrigger(dynamodboperations)
	
	
	
	return 'lambda_handler finished'


def stubCaller():
	# Saving EC2 cost
	# set all services in all clusters to zero desired count
	# set all auto scaling groups to zero desired
	# set all auto scaling groups to zero desired

	#ecsoperations = ECSOperations(ecs_clusters, ecs_dynamo_db_table_name)
	#ecsoperations.setDesiredCountsToZero()
	#ecsoperations.restoreDesiredCountsFromDB()
	
	#asoperations = AutoScalingOperations(asg_name_list, asg_dynamo_db_table_name)
	#asoperations.setDesiredCountToZero()lam
	#asoperations.restoreDesiredCounts()

	#ec2operations = EC2Operations(tags)
	#ec2operations.listInstancesByTags()
	#ec2operations.stopInstances()
	#ec2operations.startInstances()
	
	
	# rdsoperations = RDSOperations(db_instance_id, db_instance_snapshot_id)
	# rdsoperations.startDB()
	pass


def setEnvironmentState(dynamodboperations, state):
	# sets state = on or off in database
	item_to_put = {"key": {"S": environment_state_key},
	               "value": {"S": state}
	               }
	dynamodboperations.putItem(item_to_put)


def getEnvironmentState(dynamodboperations):
	response = dynamodboperations.getItem(environment_state_key)
	return str(response['Item']['value']['S'])

def switchOff(ecsoperations, asoperations, snsoperations, ec2operations, rdsoperations, dynamodboperations ,is_triggered_manually=False):
	# if the state is off already, ignore the action
	if getEnvironmentState(dynamodboperations) == "off":
		print "Environment state is already set to 'off'. Ignoring the action."
		return 1
	
	
	ecsoperations.setDesiredCountsToZero()
	asoperations.setDesiredCountToZero()
	ec2operations.stopInstances()
	rdsoperations.deleteSnapshot()
	rdsoperations.stopDB()
	
	if not is_triggered_manually:
		snsoperations.pushNotification(environment_name+" Is Down On Schedule",
									   " ")
	elif is_triggered_manually == True:
		# notify about the start of environment

		snsoperations.pushNotification(environment_name + " Is Down Manually",
		                               "Hi,\n\n"
		                               "Stage Jenkins user: " + event_global['user'] + " has initiated this action")
		
	# set the state to off
	setEnvironmentState(dynamodboperations, "off")

def switchOn(ecsoperations, asoperations, snsoperations, ec2operations, rdsoperations, dynamodboperations, is_triggered_manually=False):
	
	asoperations.restoreDesiredCounts()
	ecsoperations.restoreDesiredCountsFromDB()
	ec2operations.startInstances()
	rdsoperations.startDB()
	
	if is_triggered_manually is not True:
		snsoperations.pushNotification(environment_name+" Is Up On Schedule", " ")
	elif is_triggered_manually == True:
		# notify about the start of environment

		snsoperations.pushNotification(environment_name+" Is Up Manually",
									   "Hi,\n\n"
									   "Stage Jenkins user: "+event_global['user'] + " has initiated this action")
		
		# set the state to on
		setEnvironmentState(dynamodboperations, "on")

def setIgnoreNextTrigger(dynamodboperations, count):
	response = dynamodboperations.getItem(ignore_next_trigger_key)
	item_to_put = {"key": {"S": ignore_next_trigger_key},
	               "count": {"N": str(count)}
	               }
	dynamodboperations.putItem(item_to_put)
	
def getIgnoreNextTrigger(dynamodboperations):
	response = dynamodboperations.getItem(ignore_next_trigger_key)
	
	try:
		count = int(response['Item']['count']['N'])
		return count
	except (KeyError):
		print ("key: %s not present in DB: %s" %
		       (ignore_next_trigger_key, info_dynamo_db_table_name))
		# create the entry with count  = 1
		setIgnoreNextTrigger(dynamodboperations, 0)
		response = dynamodboperations.getItem(ignore_next_trigger_key)
		count = int(response['Item']['count']['N'])
		return count
		
	
		
def pushIgnoreNextTrigger(dynamodboperations):
	
	# increment the count by 1
	try:
		setIgnoreNextTrigger(dynamodboperations,getIgnoreNextTrigger(dynamodboperations)+1)
		
		
	except(KeyError):
		print ("key: %s not present in DB: %s" %
		       (ignore_next_trigger_key, info_dynamo_db_table_name))
		# create the entry with count  = 1
		setIgnoreNextTrigger(dynamodboperations, 1)
	
		
def popIgnoreNextTrigger(dynamodboperations):
	setIgnoreNextTrigger(dynamodboperations,getIgnoreNextTrigger(dynamodboperations)-1)
	



#lambda_handler({"action" : "pre-schedule-notify-off"}, None)
#lambda_handler({"action" : "manual-switch-on", "user": "admin"}, None)
#lambda_handler({"action" : "manual-switch-off", "user": "testing"}, None)
#lambda_handler({"action" : "ignore-next-trigger", "user":"admin" }, None)
