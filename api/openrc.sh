export OS_AUTH_URL=https://os-api.hostvds.com/identity
# export OS_PROJECT_ID=
export OS_PROJECT_NAME="hostvds-bb9dd16b-878e-4c2c-b18b-9f4d51ef527f"
export OS_USER_DOMAIN_NAME="Default"
if [ -z "$OS_USER_DOMAIN_NAME" ]; then unset OS_USER_DOMAIN_NAME; fi
export OS_PROJECT_DOMAIN_ID="default"
if [ -z "$OS_PROJECT_DOMAIN_ID" ]; then unset OS_PROJECT_DOMAIN_ID; fi
# unset v2.0 items in case set
unset OS_TENANT_ID
unset OS_TENANT_NAME
# In addition to the owning entity (tenant), OpenStack stores the entity
# performing the action as the **user**.
export OS_USERNAME="hostvds-bb9dd16b-878e-4c2c-b18b-9f4d51ef527f"
export OS_PASSWORD="_FmszeAelUUtmHl6YcvE8kl1I8w"
# If your configuration has multiple regions, we set that information here.
# OS_REGION_NAME is optional and only valid in certain environments.
export OS_REGION_NAME="eu-west2"
# Don't leave a blank variable, unset it if it was empty
if [ -z "$OS_REGION_NAME" ]; then unset OS_REGION_NAME; fi
export OS_INTERFACE=public
export OS_IDENTITY_API_VERSION=3