const f = require("node-fetch");

exports.rossum_hook_request_handler = async ({
  base_url,
  rossum_authorization_token,
  form,
  hook,
}) => {
  let response;
  let prompt;

  if (form) {
    const request = await f(`${base_url}/api/v1/internal/assist/chat`, {
      method: "POST",
      body: JSON.stringify({
        prompt: form.prompt
      }),
      headers: {
        'Authorization': `Bearer ${rossum_authorization_token}`,
        "Content-Type": "application/json"
      }
    })

    if (request.status !== 200) {
      return {
        intent: {
          error: {
            message: `O wee, there was some error :(`
          }
        }
      }
    }

    const json = await request.json()
    response = json.results.find(result => result.type !== "prompt")?.message
    prompt = json.results.find(result => result.type === "prompt")?.message

    if (!response) {
      return {
        intent: {
          error: {
            message: `O wee, copilot does not know :(`
          }
        }
      }
    }
  }

  return {
    intent: {
      form: {
        width: 700,
        hook,
        defaultValue: {
          prompt,
        },
        uiSchema: {
          "type": "Group",
          "label": "🌟 Ask anything!",
          "elements": [
            ...(response ? [{
              "type": "PromptResult",
              "text": response
            }] : []),
            {
              "type": "Control",
              "scope": "#/properties/prompt",
              options: {
                multi: true
              }
            }
          ]
        },
        schema: {
          "properties": {
            "prompt": {
              "type": "string"
            }
          }
        }
      }
    }
  }
};
