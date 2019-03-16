# k8s-sqs-autoscaler
Kubernetes pod autoscaler based on queue size in AWS SQS
This is based on the original work done by [Kyle Barton](https://medium.com/@kyle_26541) that I found here: https://medium.com/@kyle_26541/autoscaling-kubernetes-based-on-sqs-queue-size-8f08f73b4e2b
I changed it to work on Openshift version 1.5

## Usage
Update and apply the files inside openshift-configs folder.
Also run the following after:
```oc adm policy add-cluster-role-to-user customautoscaler  system:serviceaccount:[namespace]:customautoscaler```

## Options
- --sqs-queue-url=queue-url-to-watch **# required**
- --kubernetes-deployment=deplyment-name **# required**
- --kubernetes-namespace=$(K8S_NAMESPACE) **# required**
- --aws-region=eu-west-1 **# required**
- --poll-period=10 **# optional**
- --scale-down-cool-down=30 **# optional**
- --scale-up-cool-down=30 **# optional**
- --scale-up-messages=100 **# optional**
- --scale-down-messages=100 **# optional**
- --max-pods=20 **# optional**
- --min-pods=1 **# optional**

## Debugging
Enable variable **LOGGING_LEVEL** inside the pod with log level of INFO, ERROR, DEBUG