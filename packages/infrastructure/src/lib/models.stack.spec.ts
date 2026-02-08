import * as cdk from 'aws-cdk-lib'
import { Template } from 'aws-cdk-lib/assertions'
import { ModelsStack } from './models.stack'

describe('ModelsStack', () => {
  const app = new cdk.App()
  const stack = new ModelsStack(app, 'TestModelsStack', {
    deploymentEnvironment: 'development'
  })
  const template = Template.fromStack(stack)

  it('creates an S3 bucket with versioning', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      VersioningConfiguration: {
        Status: 'Enabled'
      }
    })
  })

  it('creates bucket with correct naming', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      BucketName: 'ics-anomaly-detection-models-development'
    })
  })

  it('enables S3 managed encryption', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      BucketEncryption: {
        ServerSideEncryptionConfiguration: [
          {
            ServerSideEncryptionByDefault: {
              SSEAlgorithm: 'AES256'
            }
          }
        ]
      }
    })
  })

  it('blocks public access', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      PublicAccessBlockConfiguration: {
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true
      }
    })
  })

  it('creates SSM parameters for bucket info', () => {
    template.hasResourceProperties('AWS::SSM::Parameter', {
      Name: '/ics-anomaly-detection/development/models/bucket-name'
    })

    template.hasResourceProperties('AWS::SSM::Parameter', {
      Name: '/ics-anomaly-detection/development/models/bucket-arn'
    })
  })
})
