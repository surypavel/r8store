const custom = {
    "url": "https://elis.develop.r8.lol/api/v1/hook_templates/25",
    "metadata": {},
    "events": [],
    "test": {},
    "settings": {},
    "settings_schema": null,
    "secrets_schema": {
        "type": "object",
        "additionalProperties": {
            "type": "string"
        }
    },
    "config": {
        "url": ""
    },
    "settings_description": [],
    "token_lifetime_s": null,
    "name": "Coupa Integration",
    "type": "webhook",
    "sideload": [],
    "description": "Integrate Rossum with Coupa. Automatically export Documents to Coupa, replicate Master Data in Rossum, and keep them up to date.",
    "extension_source": "rossum_store",
    "guide": "",
    "read_more_url": null,
    "extension_image_url": "https://rossum.s3.eu-west-1.amazonaws.com/rossum-store-assets/sap/Coupa+Integration.png",
    "store_description": "<div style=\"line-height: 1.8;\">\r\n\r\n    <img style=\"padding-bottom: 20px; width: 100%\"\r\n         src=\"https://rossum.s3.eu-west-1.amazonaws.com/rossum-store-assets/sap/Coupa+Integration.png\"\r\n         alt=\"Coupa Integration picture\">\r\n\r\n<p>Simplify your operations with the integration of Rossum and Coupa. Streamline your document export to Coupa, maintain synchronized master data in Rossum, and ensure up-to-date records.</p>\r\n\r\n<p>The Coupa Integration is a pre-configured integration by Rossum, facilitating seamless transfer of invoice data from Rossum to Coupa. This integration accelerates processing, relieving your Accounts Payable team from low value manual tasks, and assures invoice accuracy with minimal human intervention.</p>\r\n\r\n<p>The solution features Coupa's master data replication in Rossum. The custom business logic configuration ensures precise extraction, matching, or calculation of data for reliable invoice creation in Coupa and export of extracted invoice data to Coupa.</p>\r\n\r\n<p>The Coupa Integration leverages SFTP for two-way data communication with Coupa, leading to successful document generation in Coupa. See all the features of this product in our <a href=\"https://rossum.ai/help/wp-content/uploads/2022/10/Coupa-Integration-Service-Product-Sheet-.pdf\"><b>product sheet</b></a>.</p>\r\n\r\n<p>This integration is a paid add-on, request a demo below and get a quote.</p>",
    "external_url": "https://go.rossum.ai/coupa-extention-request",
    "use_token_owner": true,
    "order": 6,
    "install_action": "request_access"
};

exports.rossum_hook_request_handler = async ({
  payload,
}) => {
  if (payload["name"] == "get_hook_template_list") {
    return { custom: custom };
  }

  if (payload["name"] == "get_hook_template_version") {
    return ["0.1"];
  }

  if (payload["name"] == "checkout_hook_template") {
    return custom;
  }
};
