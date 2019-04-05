import sys
import json
import boto3
from time import sleep, time
from logs.log import logger
from os import environ, path
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Activate trace only if debug is enabled
if environ.get('LOGGING_LEVEL') != 'DEBUG':
    sys.tracebacklimit = 0


class SQSPoller:

    options = None
    sqs_client = None
    last_message_count = None

    def __init__(self, options):
        if environ.get('SERVICE_ACCOUNT_TOKEN') is None:
            if path.isfile('/run/secrets/kubernetes.io/serviceaccount/token'):
                self.token = open(
                    '/run/secrets/kubernetes.io/serviceaccount/token').read()
            else:
                logger.error(
                    'Failed to fetch token of serviceaccount. Unable to continue')
                sys.exit(1)
        else:
            self.token = environ.get('SERVICE_ACCOUNT_TOKEN')

        if environ.get('KUBERNETES_PORT_443_TCP_ADDR') is None or environ.get('KUBERNETES_PORT_443_TCP_PORT') is None:
            logger.error('Cannot find environment variables with api endpoint')
            logger.error(
                'Environments missing are KUBERNETES_PORT_443_TCP_ADDR and KUBERNETES_PORT_443_TCP_PORT')
            sys.exit(1)

        self.k8s_endpoint = environ.get('KUBERNETES_PORT_443_TCP_ADDR') + \
            ':' + environ.get('KUBERNETES_PORT_443_TCP_PORT')
        self.options = options
        self.sqs_client = boto3.client('sqs')
        self.last_scale_up_time = time()
        self.last_scale_down_time = time()

    def message_count(self):
        response = self.sqs_client.get_queue_attributes(
            QueueUrl=self.options.sqs_queue_url,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        logger.info("Got %i messages on queue %s" %
                    (int(response['Attributes']['ApproximateNumberOfMessages']), self.options.sqs_queue_url))
        return int(response['Attributes']['ApproximateNumberOfMessages'])

    def poll(self):
        message_count = self.message_count()
        t = time()
        if message_count >= self.options.scale_up_messages:
            if t - self.last_scale_up_time > self.options.scale_up_cool_down:
                self.scale_up()
                logger.info("Scaling up")
                self.last_scale_up_time = t
            else:
                logger.debug("Waiting for scale up cooldown")
        if message_count <= self.options.scale_down_messages:
            if t - self.last_scale_down_time > self.options.scale_down_cool_down:
                logger.info("Scaling down")
                self.scale_down()
                self.last_scale_down_time = t
            else:
                logger.debug("Waiting for scale down cooldown")

        # code for scale to use msg_count
        sleep(self.options.poll_period)

    def scale_up(self):
        deployment = self.deployment()
        # logger.info(json.dumps(deployment))
        if deployment['spec']['replicas'] < self.options.max_pods:
            logger.info("Scaling up")
            deployment['spec']['replicas'] += 1
            self.update_deployment(deployment)
            logger.info("Replicas: %s" % deployment['spec']['replicas'])
        elif deployment['spec']['replicas'] > self.options.max_pods:
            logger.info("Scaling down")
            self.scale_down()
        else:
            logger.info("Max pods reached")

    def scale_down(self):
        deployment = self.deployment()
        if deployment['spec']['replicas'] > self.options.min_pods:
            logger.info("Scaling Down")
            deployment['spec']['replicas'] -= 1
            self.update_deployment(deployment)
        elif deployment['spec']['replicas'] < self.options.min_pods:
            self.scale_up()
        else:
            logger.info("Min pods reached")

    def deployment(self):
        logger.debug("loading deployment: {} from namespace: {}".format(
            self.options.kubernetes_deployment, self.options.kubernetes_namespace))
        deployments = requests.get("https://"+self.k8s_endpoint + "/oapi/v1/deploymentconfigs/?fieldSelector=metadata.name%3D"+self.options.kubernetes_deployment,
                                   timeout=5,
                                   verify=False,
                                   headers={
                                       "Authorization": "Bearer "+self.token,
                                       "Accept": "application/json"
                                   }).json()
        if not deployments['items']:
            raise Exception('No deploymentconfig found with that name!')
        return deployments['items'][0]

    def update_deployment(self, deployment):
        # Update the deployment
        data = '{"spec":{"replicas":%i}}' % deployment['spec']['replicas']
        api_response = requests.patch("https://"+self.k8s_endpoint + "/oapi/v1/namespaces/"+self.options.kubernetes_namespace+"/deploymentconfigs/"+self.options.kubernetes_deployment+"/scale",
                                      timeout=5,
                                      verify=False,
                                      headers={
                                          "Authorization": "Bearer " + self.token,
                                          "Accept": "application/json",
                                          "Content-Type": "application/merge-patch+json"
                                      },
                                      data=data)
        logger.debug("Deployment updated. status='%s'" %
                     str(api_response.status_code))

    def run(self):
        options = self.options
        logger.debug("Starting poll for {} every {}s".format(
            options.sqs_queue_url, options.poll_period))
        while True:
            self.poll()


def run(options):
    """
    poll_period is set as as part of k8s deployment env variable
    sqs_queue_url is set as as part of k8s deployment env variable
    """
    SQSPoller(options).run()
