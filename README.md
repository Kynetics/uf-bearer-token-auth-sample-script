# UpdateFactory sample script for using API Clients

# Requirements
- Python 3

# Script usage

The script exchanges API Client credentials for a Bearer token, then uses the token to authenticate a Management API call. Usage:

python3 validate_bearer_token.py \
    --mgmt-url https://mgmt.business.updatefactory.io \
    --tenant MY_TENANT \
    --client-name my-api-client \
    --client-secret my-client-secret


# License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
