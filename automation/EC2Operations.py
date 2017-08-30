import boto3
import json
class EC2Operations:
    ec2_client = boto3.client('ec2')
    
    def __init__(self, tags):
        self.tags = tags

    def listInstancesByTags(self):

        # input: dictionay of tags: name:value, name:value
        # ouput : list of ec2 instances having those tags and those corresponding values

        # extracting tags in the form accepted by boto3
        tag_filter=[]
        for i in range(len(self.tags)):
            for key, value in self.tags[i].iteritems():
                tag_filter.append({"Name":"tag:"+key, "Values": [value]})

        response = self.ec2_client.describe_instances(Filters=tag_filter)

        instances_list=[]
        for i in range(len(response['Reservations'])):
            instances_list.append(response['Reservations'][i]['Instances'][0]['InstanceId'])
        
        print "instances matched the tags: "+ json.dumps(instances_list)
        
        return instances_list

    def stopInstances(self):
        # input: list of instances to stop
        # fire stop instance api call
        # return api call status of each instances

        instances_list = self.listInstancesByTags()
        try:
            response = self.ec2_client.stop_instances(InstanceIds=instances_list, Force=True)
            print json.dumps(response)
            return response
        except Exception as exp:
            print ("Exception: ", exp)
            return "Error"
        
    def startInstances(self):
        instances_list = self.listInstancesByTags()
        try:
            response = self.ec2_client.start_instances(InstanceIds=instances_list)
            print json.dumps(response)
            return response
        except Exception as exp:
            print ("Exception: ", exp)
            return "Error"