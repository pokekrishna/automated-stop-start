import boto3

class DynamoDBOperations:
	dynamodb_client = boto3.client('dynamodb')
	def __init__(self, table_name):
		self.table_name = table_name
		
	
	
	def putItem (self, item_to_put):
		# item_to_put should be a dictionary in the form  acceptable
		# by DynamoDB

		# item_to_put will be inserted as is - not validation

		print ("Inserting in table : %s. Data: %s" % (self.table_name,
		                                              str(item_to_put)) )
		
		response = self.dynamodb_client.put_item(TableName=self.table_name,
		                                         Item=item_to_put
		                                         )
	
	def getItem (self, key):
		response = self.dynamodb_client.get_item(
			TableName=self.table_name,
			Key={'key': {'S': key}})
		return response