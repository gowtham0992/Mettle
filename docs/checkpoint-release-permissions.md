# Upgrade an existing deployment to durable checkpoints

This migration guide applies to installations created before durable checkpoints.
New installations should use the current web template. The hosted deployment
has completed this migration and signed-in end-to-end acceptance; an overnight
real-date continuation test remains outstanding. See [verification scope](recovery-checkpoints.md).

The existing `MettleWebDeployer` can publish web code and static assets. It cannot update infrastructure. Do not solve this by attaching AdministratorAccess or granting IAM-policy editing to that deployer.

## Administrator-reviewed changes

Use a non-root administrator session in the Mettle account. Resolve the exact account and packet bucket from the existing `MettleWeb` stack; all identifiers in the checked-in policies are examples, not deployment values. Preserve existing attached and inline policies.

1. Add `infra/web/iam/checkpoint-release-deployer-policy.json` as a supplemental policy on `MettleWebDeployer`. Replace only the sample account ID. This adds scheduler **code** updates and read-only inspection of the existing stack. It does not permit Lambda configuration, role changes, IAM changes, stack changes, or deletion.
2. Apply the storage-permission and retention changes from `infra/web/template.yaml` through an administrator-reviewed CloudFormation change set. Confirm the diff contains only the intended release changes, with no resource replacement, public access, trust-policy change, or authentication change. The scheduler-storage JSON shows the exact additional permission for review; prefer the template-owned inline policy rather than attaching a duplicate policy outside CloudFormation.
3. The retention change makes private artifacts eligible for deletion after 31 days instead of one day. This includes packet PDFs and checkpoints. Workflow records become eligible for deletion 30 days after their last update. These are lifecycle/TTL policies, not an exact deletion-time guarantee.

Updating Lambda code allows that code to act with the function's existing execution-role permissions. It is security-sensitive even though the resource is narrowly scoped. The administrator must review and approve this extension.

## Deployment order

Build and verify the runtime and Lambda artifacts first. Apply storage/worker IAM changes before enabling the checkpoint-dependent gateway. Deploy the compatible runtime, then update **both** `mettle-web` and `mettle-scheduler` code, and finally publish the static UI. The scheduler handler remains configured separately even when both functions use the same packaged code.

The existing direct web deployment script updates only `mettle-web`; it is not sufficient by itself for this release. Either use the administrator-reviewed stack deployment for both function artifacts or explicitly update the scheduler artifact using the scoped deployer after the prerequisite changes.

After deployment, test a synthetic recovery through review, fresh-runtime restoration, evidence, final approval, and scheduled continuation. Do not send to real trades. Verify replay and uncertain-outcome holds. Preserve the prior artifacts, but do not roll a checkpoint-bearing runtime back to a version without restore support.

## Boundaries

- No `iam:*`, `iam:PutRolePolicy`, `iam:PassRole`, or CloudFormation write permission is added to the deployer.
- No new IAM user, access key, role trust, public endpoint, or bucket sharing is introduced.
- IAM syntax checks and local policy tests are not proof of deployed authorization. After administrator application, verify the actual caller and permission behavior before release.
- If there is no existing non-root administrator, stop for account-owner direction; do not create one or silently use root.
