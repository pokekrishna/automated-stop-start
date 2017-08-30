import boto3
class RDSOperations:
	rds_client = boto3.client('rds')
	def __init__(self, db_id, db_snapshot_id):
		self.db_id =db_id
		self.db_snapshot_id = db_snapshot_id
		pass
	
	
	def stopDB(self):
		print ("Stoppng RDS instance '%s' and creating snapshot '%s'" % (self.db_id, self.db_snapshot_id))
		
		response = self.rds_client.stop_db_instance(
			DBInstanceIdentifier=self.db_id,
			DBSnapshotIdentifier=self.db_snapshot_id
		)
		# print response
		
	def startDB(self):
		print ("Starting RDS instance '%s'" % (self.db_id))
		response = self.rds_client.start_db_instance(
			DBInstanceIdentifier=self.db_id
		)
		# print response
	def deleteSnapshot(self):
		response = self.rds_client.delete_db_snapshot(
			DBSnapshotIdentifier=self.db_snapshot_id
		)
		print ("Deleted Snapshot ID: '%s'" % (self.db_snapshot_id))