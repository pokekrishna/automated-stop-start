import boto3
class SNSOperations:
	
	sns_client = boto3.client('sns')
	
	def __init__(self, topic_arn, suppress_notifications=False):
		self.topic_arn = topic_arn
		self.suppress_notifications = suppress_notifications
		
	def pushNotification(self, subject, message):
		if not self.suppress_notifications:
			response = self.sns_client.publish(
				TopicArn=self.topic_arn,
				Message=message,
				Subject=subject,
			
			)