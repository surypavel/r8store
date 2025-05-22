const custom = {
    "events": [],
    "config": {
      "code": `exports.rossum_hook_request_handler = async ({ payload }) => {};`,
      "runtime": "nodejs22.x"
    },
    "description": "Custom added extension.",
    "name": "Custom added extension",
    "type": "function",
    "guide": "",
    "extension_image_url": "https://surypavel.github.io/r8store/static/thermo.webp",
    "store_description": "Check for sender_address of a current annotation and check the weather (temperature). This shows how you can communicate with external APIs.",
    "hook_integrations": []
  };

exports.rossum_hook_request_handler = async ({ payload }) => {
  if (payload["name"] == "get_hook_template_list") {
    return [{ id: "custom", hook_template: custom }];
  }

  if (payload["name"] == "get_hook_template_version") {
    return ["0.1"];
  }

  if (payload["name"] == "checkout_hook_template") {
    return custom;
  }
};
