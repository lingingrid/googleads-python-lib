#!/usr/bin/python
#
# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This uses the BatchJobService to create a complete Campaign.

The complete Campaign created by this example also includes AdGroups and
KeyWords.

Api: AdWordsOnly
"""

import logging
import random
import time
import urllib2
import uuid


from batch_job_util import BatchJobHelper
from batch_job_util import BatchJobServiceIdGenerator
from googleads import adwords


# Set logging configuration
logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.transport').setLevel(logging.DEBUG)


NUMBER_OF_CAMPAIGNS_TO_ADD = 2
NUMBER_OF_ADGROUPS_TO_ADD = 2
NUMBER_OF_KEYWORDS_TO_ADD = 5
MAX_POLL_ATTEMPTS = 5
PENDING_STATUSES = ('ACTIVE', 'AWAITING_FILE')


def main(client, number_of_campaigns, number_of_adgroups, number_of_keywords):
  # Initialize BatchJobHelper
  batch_job_helper = BatchJobHelper(client)

  batch_job = AddBatchJob(client)
  upload_url = batch_job['uploadUrl']['url']
  batch_job_id = batch_job['id']

  logging.info('Created BatchJob with ID "%d", status "%s", and upload URL '
               '"%s"', batch_job['id'], batch_job['status'], upload_url)

  operations = BuildUploadUrlOperations(batch_job_helper, number_of_campaigns,
                                        number_of_adgroups, number_of_keywords)

  batch_job_helper.UploadBatchJobOperations(
      upload_url, *operations)

  download_url = GetBatchJobDownloadUrlWhenReady(client, batch_job_id)
  response = urllib2.urlopen(download_url)
  logging.info('Downloaded following response:\n%s', response.read())


def AddBatchJob(client):
  """Add a new BatchJob to upload operations to.

  Args:
    client: an instantiated AdWordsClient used to retrieve the BatchJob.

  Returns:
    The new BatchJob created by the request.
  """
  # Initialize appropriate service.
  batch_job_service = client.GetService('BatchJobService', version='v201509')
  # Create a BatchJob
  batch_job_operations = [{
      'operand': {},
      'operator': 'ADD'
  }]
  return batch_job_service.mutate(batch_job_operations)['value'][0]


def BuildAdGroupAdOperations(adgroup_operations):
  """Builds the operations adding a TextAd to each AdGroup.

  Args:
    adgroup_operations: a list containing the operations that will add AdGroups.

  Returns:
    a list containing the operations that will create a new TextAd for each of
    the provided AdGroups.
  """
  adgroup_ad_operations = [
      {
          # The xsi_type of the operation can usually be guessed by the API
          # because a given service only handles one type of operation.
          # However, batch jobs process operations of different types, so
          # the xsi_type must always be explicitly defined for these
          # operations.
          'xsi_type': 'AdGroupAdOperation',
          'operand': {
              'adGroupId': adgroup_operation['operand']['id'],
              'ad': {
                  'xsi_type': 'TextAd',
                  'headline': 'Luxury Cruise to Mars',
                  'description1': 'Visit the Red Planet in style.',
                  'description2': 'Low-gravity fun for everyone!',
                  'displayUrl': 'www.example.com',
                  'finalUrls': ['http://www.example.com/1']
              }
          },
          'operator': 'ADD'
      }
      for adgroup_operation in adgroup_operations]

  return adgroup_ad_operations


def BuildAdGroupCriterionOperations(adgroup_operations, number_of_keywords=1):
  """Builds the operations adding a Keyword Criterion to each AdGroup.

  Args:
    adgroup_operations: a list containing the operations that will add AdGroups.
    number_of_keywords: an int defining the number of Keywords to be created.

  Returns:
    a list containing the operations that will create a new Keyword Criterion
    associated with each provided AdGroup.
  """
  criterion_operations = [
      {
          # The xsi_type of the operation can usually be guessed by the API
          # because a given service only handles one type of operation.
          # However, batch jobs process operations of different types, so
          # the xsi_type must always be explicitly defined for these
          # operations.
          'xsi_type': 'AdGroupCriterionOperation',
          'operand': {
              'xsi_type': 'BiddableAdGroupCriterion',
              'adGroupId': adgroup_operation['operand']['id'],
              'criterion': {
                  'xsi_type': 'Keyword',
                  # Make 50% of keywords invalid to demonstrate error handling.
                  'text': 'mars%s%s' % (i, '!!!' if i % 2 == 0 else ''),
                  'matchType': 'BROAD'
              }
          },
          'operator': 'ADD'
      }
      for adgroup_operation in adgroup_operations
      for i in range(number_of_keywords)]

  return criterion_operations


def BuildAdGroupOperations(batch_id_generator,
                           campaign_operations, number_of_adgroups=1):
  """Builds the operations adding desired number of AdGroups to given Campaigns.

  Note: When the AdGroups are created, they will have a different Id than those
  generated here as a temporary Id. This is just used to identify them in the
  BatchJobService.

  Args:
    batch_id_generator: a BatchJobServiceIdGenerator instance.
    campaign_operations: a list containing the operations that will add
      Campaigns.
    number_of_adgroups: an int defining the number of AdGroups to be created per
      Campaign.

  Returns:
    a list containing the operations that will add the desired number of
    AdGroups to each of the provided Campaigns.
  """
  adgroup_operations = [
      {
          # The xsi_type of the operation can usually be guessed by the API
          # because a given service only handles one type of operation.
          # However, batch jobs process operations of different types, so
          # the xsi_type must always be explicitly defined for these
          # operations.
          'xsi_type': 'AdGroupOperation',
          'operand': {
              'campaignId': campaign_operation['operand']['id'],
              'id': batch_id_generator.GetId(),
              'name': 'Batch Ad Group #%s' % uuid.uuid4(),
              'biddingStrategyConfiguration': {
                  'bids': [
                      {
                          'xsi_type': 'CpcBid',
                          'bid': {
                              'microAmount': 10000000
                          }
                      }
                  ]
              }
          },
          'operator': 'ADD'
      }
      for campaign_operation in campaign_operations
      for _ in range(number_of_adgroups)]

  return adgroup_operations


def BuildBudgetOperations(batch_id_generator):
  """Builds the operations needed to create a new Budget.

  Note: When the Budget is created, it will have a different Id than the one
  generated here as a temporary Id. This is just used to identify it in the
  BatchJobService.

  Args:
    batch_id_generator: a BatchJobServiceIdGenerator instance.

  Returns:
    a list containing the operation that will create a new Budget.
  """
  # A list of operations creating a Budget.
  budget_operations = [{
      # The xsi_type of the operation can usually be guessed by the API because
      # a given service only handles one type of operation. However, batch jobs
      # process operations of different types, so the xsi_type must always be
      # explicitly defined for these operations.
      'xsi_type': 'BudgetOperation',
      'operand': {
          'name': 'Batch budget #%s' % uuid.uuid4(),
          # This is a temporary Id used by the BatchJobService to identify the
          # Budget for operations that require a budgetId.
          'budgetId': batch_id_generator.GetId(),
          'amount': {
              'microAmount': '50000000'
          },
          'deliveryMethod': 'STANDARD',
          'period': 'DAILY'
      },
      'operator': 'ADD'
  }]

  return budget_operations


def BuildCampaignCriterionOperations(campaign_operations):
  """Builds the operations needed to create Negative Campaign Criterion.

  Args:
    campaign_operations: a list containing the operations that will add
      Campaigns.

  Returns:
    a list containing the operations that will create a new Negative Campaign
    Criterion associated with each provided Campaign.
  """
  criterion_operations = [
      {
          # The xsi_type of the operation can usually be guessed by the API
          # because a given service only handles one type of operation.
          # However, batch jobs process operations of different types, so
          # the xsi_type must always be explicitly defined for these
          # operations.
          'xsi_type': 'CampaignCriterionOperation',
          'operand': {
              'xsi_type': 'NegativeCampaignCriterion',
              'campaignId': campaign_operation['operand']['id'],
              'criterion': {
                  'xsi_type': 'Keyword',
                  'matchType': 'BROAD',
                  'text': 'venus'
              }
          },
          'operator': 'ADD'
      }
      for campaign_operation in campaign_operations]

  return criterion_operations


def BuildCampaignOperations(batch_id_generator,
                            budget_operations, number_of_campaigns=1):
  """Builds the operations needed to create a new Campaign.

  Note: When the Campaigns are created, they will have a different Id than those
  generated here as a temporary Id. This is just used to identify them in the
  BatchJobService.

  Args:
    batch_id_generator: a BatchJobServiceIdGenerator instance.
    budget_operations: a list containing the operation that will add the budget
      used by these Campaigns.
    number_of_campaigns: an int number defining the number of campaigns to be
      created.

  Returns:
    a list containing the operations to create the desired number of Campaigns.
  """
  # Grab the temporary budgetId to associate with the new Campaigns.
  budget_id = budget_operations[0]['operand']['budgetId']

  campaign_operations = [
      {
          # The xsi_type of the operation can usually be guessed by the API
          # because a given service only handles one type of operation.
          # However, batch jobs process operations of different types, so
          # the xsi_type must always be explicitly defined for these
          # operations.
          'xsi_type': 'CampaignOperation',
          'operand': {
              'name': 'Batch Campaign #%s' % uuid.uuid4(),
              'status': 'PAUSED',
              # This is a temporary Id used by the BatchJobService to identify
              # the Campaigns for operations that require a campaignId.
              'id': batch_id_generator.GetId(),
              'advertisingChannelType': 'SEARCH',
              # Note that only the budgetId is required
              'budget': {
                  'budgetId': budget_id
              },
              'biddingStrategyConfiguration': {
                  'biddingStrategyType': 'MANUAL_CPC'
              }
          },
          'operator': 'ADD'
      }
      for _ in range(number_of_campaigns)]

  return campaign_operations


def BuildUploadUrlOperations(batch_job_helper, number_of_campaigns,
                             number_of_adgroups, number_of_keywords):
  """Builds a list of operations that will be uploaded to the BatchJobService.

  Args:
    batch_job_helper: a BatchJobHelper instance used to construct operations.
    number_of_campaigns: an int defining the number of Campaigns to be created.
    number_of_adgroups: an int defining the number of AdGroups to be created.
    number_of_keywords: an int defining the number of Keywords to be created.

  Returns:
    A tuple of str, where each is a set of operations for distinct services.
  """
  # Initialize BatchJobServiceIdGenerator.
  batch_id_generator = BatchJobServiceIdGenerator()

  # Build BudgetOperations and retrieve in XML form.
  budget_operations = BuildBudgetOperations(batch_id_generator)
  budget_request_xml = batch_job_helper.GenerateRawRequestXML(
      budget_operations, 'BudgetService')
  budget_operations_xml = batch_job_helper.ExtractOperations(
      budget_request_xml)
  # Build CampaignOperations and retrieve in XML form.
  campaign_operations = BuildCampaignOperations(
      batch_id_generator, budget_operations, number_of_campaigns)
  campaign_request_xml = batch_job_helper.GenerateRawRequestXML(
      campaign_operations, 'CampaignService')
  campaign_operations_xml = batch_job_helper.ExtractOperations(
      campaign_request_xml)
  # Build CampaignCriterionOperations and retrieve in XML form.
  campaign_criterion_operations = BuildCampaignCriterionOperations(
      campaign_operations)
  campaign_criterion_request_xml = batch_job_helper.GenerateRawRequestXML(
      campaign_criterion_operations, 'CampaignCriterionService')
  campaign_criterion_operations_xml = (
      batch_job_helper.ExtractOperations(
          campaign_criterion_request_xml))
  # Build AdGroupOperations and retrieve in XML form.
  adgroup_operations = BuildAdGroupOperations(
      batch_id_generator, campaign_operations, number_of_adgroups)
  adgroup_request_xml = batch_job_helper.GenerateRawRequestXML(
      adgroup_operations, 'AdGroupService')
  adgroup_operations_xml = batch_job_helper.ExtractOperations(
      adgroup_request_xml)
  # Build AdGroupCriterionOperations and retrieve in XML form.
  adgroup_criterion_operations = BuildAdGroupCriterionOperations(
      adgroup_operations, number_of_keywords)
  adgroup_criterion_request_xml = batch_job_helper.GenerateRawRequestXML(
      adgroup_criterion_operations, 'AdGroupCriterionService')
  adgroup_criterion_operations_xml = (
      batch_job_helper.ExtractOperations(
          adgroup_criterion_request_xml))
  # Build AdGroupAdOperations and retrieve in XML form.
  adgroup_ad_operations = BuildAdGroupAdOperations(adgroup_operations)
  adgroup_ad_request_xml = batch_job_helper.GenerateRawRequestXML(
      adgroup_ad_operations, 'AdGroupAdService')
  adgroup_ad_operations_xml = batch_job_helper.ExtractOperations(
      adgroup_ad_request_xml)

  return (budget_operations_xml, campaign_operations_xml,
          campaign_criterion_operations_xml, adgroup_operations_xml,
          adgroup_criterion_operations_xml, adgroup_ad_operations_xml)


def GetBatchJob(client, batch_job_id):
  """Retrieves the BatchJob with the given id.

  Args:
    client: an instantiated AdWordsClient used to retrieve the BatchJob.
    batch_job_id: a long identifying the BatchJob to be retrieved.
  Returns:
    The BatchJob associated with the given id.
  """
  batch_job_service = client.GetService('BatchJobService')

  selector = {
      'fields': ['Id', 'Status', 'DownloadUrl'],
      'predicates': [
          {
              'field': 'Id',
              'operator': 'EQUALS',
              'values': [batch_job_id]
          }
      ]
  }

  return batch_job_service.get(selector)['entries'][0]


def GetBatchJobDownloadUrlWhenReady(client, batch_job_id,
                                    max_poll_attempts=MAX_POLL_ATTEMPTS):
  """Retrieves the downloadUrl when the BatchJob is complete.

  Args:
    client: an instantiated AdWordsClient used to poll the BatchJob.
    batch_job_id: a long identifying the BatchJob to be polled.
    max_poll_attempts: an int defining the number of times the the BatchJob will
      be checked to determine whether it has completed.

  Returns:
    A str containing the downloadUrl of the completed BatchJob.

  Raises:
    Exception: If the BatchJob hasn't finished after the maximum poll attempts
      have been made.
  """
  batch_job = GetBatchJob(client, batch_job_id)
  poll_attempt = 0
  while (poll_attempt in range(max_poll_attempts) and
         batch_job['status'] in PENDING_STATUSES):
    sleep_interval = (30 * (2 ** poll_attempt) +
                      (random.randint(0, 10000) / 1000))
    logging.info('Batch Job not ready, sleeping for %s seconds.',
                 sleep_interval)
    time.sleep(sleep_interval)
    batch_job = GetBatchJob(client, batch_job_id)
    poll_attempt += 1

    if 'downloadUrl' in batch_job:
      url = batch_job['downloadUrl']['url']
      logging.info(
          'Batch Job with Id "%s", Status "%s", and DownloadUrl "%s" ready.',
          batch_job['id'], batch_job['status'], url)
      return url
  raise Exception('Batch Job not finished downloading. Try checking later.')


if __name__ == '__main__':
  # Initialize client object.
  adwords_client = adwords.AdWordsClient.LoadFromStorage()
  main(adwords_client, NUMBER_OF_CAMPAIGNS_TO_ADD, NUMBER_OF_ADGROUPS_TO_ADD,
       NUMBER_OF_KEYWORDS_TO_ADD)