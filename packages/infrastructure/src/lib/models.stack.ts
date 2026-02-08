import * as cdk from 'aws-cdk-lib'
import * as s3 from 'aws-cdk-lib/aws-s3'
import * as ssm from 'aws-cdk-lib/aws-ssm'
import * as iam from 'aws-cdk-lib/aws-iam'
import type { Construct } from 'constructs'

interface ModelsStackProps extends cdk.StackProps {
  deploymentEnvironment: 'development' | 'staging' | 'production'
}

/**
 * Stack for ML model storage infrastructure.
 *
 * Creates an S3 bucket for storing trained anomaly detection models
 * with versioning enabled for rollback capability.
 */
export class ModelsStack extends cdk.Stack {
  public readonly bucket: s3.IBucket
  private readonly deploymentEnvironment: string

  constructor(scope: Construct, id: string, props: ModelsStackProps) {
    super(scope, id, props)

    this.deploymentEnvironment = props.deploymentEnvironment

    this.bucket = this.createModelsBucket()
    this.createBucketPolicy()
    this.storeParameters()
    this.createOutputs()
  }

  /**
   * Create S3 bucket for model storage with versioning.
   */
  private createModelsBucket(): s3.Bucket {
    const bucket = new s3.Bucket(this, 'ModelsBucket', {
      bucketName: `ics-anomaly-detection-models-${this.deploymentEnvironment}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy:
        this.deploymentEnvironment === 'production'
          ? cdk.RemovalPolicy.RETAIN
          : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: this.deploymentEnvironment !== 'production',
      lifecycleRules: [
        {
          id: 'delete-old-versions',
          noncurrentVersionExpiration: cdk.Duration.days(90),
          enabled: true,
        },
        {
          id: 'transition-to-ia',
          noncurrentVersionTransitions: [
            {
              storageClass: s3.StorageClass.INFREQUENT_ACCESS,
              transitionAfter: cdk.Duration.days(30),
            },
          ],
          enabled: true,
        },
      ],
    })

    cdk.Tags.of(bucket).add('Project', 'ics-anomaly-detection')
    cdk.Tags.of(bucket).add('Environment', this.deploymentEnvironment)
    cdk.Tags.of(bucket).add('Purpose', 'ml-model-storage')

    return bucket
  }

  /**
   * Create bucket policy for model access.
   */
  private createBucketPolicy(): void {
    // Allow anomaly-detection service to read models
    // In production, this would be scoped to specific IAM roles
    this.bucket.addToResourcePolicy(
      new iam.PolicyStatement({
        sid: 'AllowModelRead',
        effect: iam.Effect.ALLOW,
        principals: [new iam.AccountRootPrincipal()],
        actions: ['s3:GetObject', 's3:ListBucket'],
        resources: [this.bucket.bucketArn, `${this.bucket.bucketArn}/*`],
      })
    )
  }

  /**
   * Store bucket info in SSM Parameter Store for service discovery.
   */
  private storeParameters(): void {
    new ssm.StringParameter(this, 'SSMBucketName', {
      parameterName: `/ics-anomaly-detection/${this.deploymentEnvironment}/models/bucket-name`,
      stringValue: this.bucket.bucketName,
      description: 'S3 bucket name for ML models',
    })

    new ssm.StringParameter(this, 'SSMBucketArn', {
      parameterName: `/ics-anomaly-detection/${this.deploymentEnvironment}/models/bucket-arn`,
      stringValue: this.bucket.bucketArn,
      description: 'S3 bucket ARN for ML models',
    })
  }

  /**
   * Create CloudFormation outputs.
   */
  private createOutputs(): void {
    new cdk.CfnOutput(this, 'ModelsBucketName', {
      value: this.bucket.bucketName,
      description: 'S3 bucket for ML model storage',
      exportName: `ics-models-bucket-${this.deploymentEnvironment}`,
    })

    new cdk.CfnOutput(this, 'ModelsBucketArn', {
      value: this.bucket.bucketArn,
      description: 'S3 bucket ARN for ML model storage',
    })
  }
}
