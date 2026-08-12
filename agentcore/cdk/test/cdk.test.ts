import * as cdk from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';
import { AgentCoreStack } from '../lib/cdk-stack';

test('AgentCoreStack synthesizes with empty spec', () => {
  const app = new cdk.App();
  const stack = new AgentCoreStack(app, 'TestStack', {
    spec: {
      name: 'testproject',
      version: 1,
      managedBy: 'CDK' as const,
      runtimes: [],
      memories: [],
      credentials: [],
      evaluators: [],
      onlineEvalConfigs: [],
      configBundles: [],
      policyEngines: [],
      payments: [],
      agentCoreGateways: [],
      mcpRuntimeTools: [],
      unassignedTargets: [],
      datasets: [],
      knowledgeBases: [],
    } as any,
  });
  const template = Template.fromStack(stack);
  template.hasOutput('StackNameOutput', {
    Description: 'Name of the CloudFormation Stack',
  });
});

test('Mettle runtime allows only the two approved Nova models', () => {
  const app = new cdk.App();
  const stack = new AgentCoreStack(app, 'TestMettleStack', {
    spec: {
      name: 'Mettle',
      version: 1,
      managedBy: 'CDK' as const,
      runtimes: [
        {
          name: 'MettleRecovery',
          build: 'CodeZip',
          entrypoint: 'agentcore_app.py',
          codeLocation: '.',
          runtimeVersion: 'PYTHON_3_12',
          networkMode: 'PUBLIC',
          protocol: 'HTTP',
          authorizerType: 'AWS_IAM',
        },
      ],
      memories: [],
      credentials: [],
      evaluators: [],
      onlineEvalConfigs: [],
      configBundles: [],
      policyEngines: [],
      payments: [],
      agentCoreGateways: [],
      mcpRuntimeTools: [],
      unassignedTargets: [],
      datasets: [],
      knowledgeBases: [],
    } as any,
  });

  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::IAM::Policy', {
    PolicyDocument: {
      Statement: Match.arrayWith([
        {
          Action: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream', 'bedrock:CountTokens'],
          Effect: 'Deny',
          NotResource: [
            'arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0',
            'arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0',
          ],
        },
      ]),
    },
  });
});
