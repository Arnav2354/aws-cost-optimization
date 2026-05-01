import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    
    # 1. Describe all instances
    instances_response = ec2.describe_instances()
    running_instance_ids = []
    for reservation in instances_response['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name'] == 'running':
                running_instance_ids.append(instance['InstanceId'])
    
    # 2. Describe all snapshots owned by you
    snapshots_response = ec2.describe_snapshots(OwnerIds=['self'])
    
    for snapshot in snapshots_response['Snapshots']:
        snapshot_id = snapshot['SnapshotId']
        volume_id = snapshot.get('VolumeId')
        
        if not volume_id:
            # No volume linked, delete snapshot
            delete_snapshot(ec2, snapshot_id, "No associated volume")
            continue
        
        try:
            # Get the volume
            volume_response = ec2.describe_volumes(VolumeIds=[volume_id])
            if not volume_response['Volumes']:
                # Volume not found, delete snapshot
                delete_snapshot(ec2, snapshot_id, "Volume not found")
                continue
            
            volume = volume_response['Volumes'][0]
            attachments = volume.get('Attachments', [])
            
            if not attachments:
                # Volume not attached to any instance
                delete_snapshot(ec2, snapshot_id, "Volume not attached")
                continue
            
            # If attached, check if the instance is running
            instance_id = attachments[0]['InstanceId']
            instance_response = ec2.describe_instances(InstanceIds=[instance_id])
            instance = instance_response['Reservations'][0]['Instances'][0]
            
            if instance['State']['Name'] != 'running':
                # Instance is not running
                delete_snapshot(ec2, snapshot_id, "Instance not running")
        
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidVolume.NotFound':
                 print(f"Deleting snapshot {snapshot_id} - Volume not found")
                 ec2.delete_snapshot(SnapshotId=snapshot_id)
            else:
                 print(f"Skipping {snapshot_id} - Unexpected error: {str(e)}")
    
def delete_snapshot(ec2, snapshot_id, reason):
    print(f"Deleting snapshot {snapshot_id} - {reason}")
    ec2.delete_snapshot(SnapshotId=snapshot_id)

