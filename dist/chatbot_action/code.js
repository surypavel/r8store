const fstring = {
  oneOf: [{
      type: "string",
    },
    {
      type: "object",
      properties: {
        __fstring: {
          type: "string",
        },
      },
    },
  ],
};

exports.rossum_hook_request_handler = async ({
  configure,
  annotation,
  payloads,
  base_url,
  rossum_authorization_token,
}) => {
  console.log("hi");
  if (configure === true) {
    return {
      intent: {
        form: {
          uiSchema: {
            "type": "VerticalLayout",
            "elements": [{
                "type": "Control",
                "scope": "#/properties/model"
              },
              {
                "type": "FString",
                "scope": "#/properties/prompt"
              }
            ]
          },
          schema: {
            definitions: {
              fstring
            },
            type: "object",
            properties: {
              model: {
                type: "string",
                "enum": [
                  "anthropic.claude-v2", "anthropic.claude-v2:1", "anthropic.claude-instant-v1", "amazon.titan-text-express-v1"
                ]
              },
              prompt: {
                $ref: "#/definitions/fstring",
              }
            }
          }
        }
      }
    }
  } else {
    const payload = payloads[0];
    
    try {
      const endpoint = `${base_url}/api/v1/internal/chatbot`;
      const response = await fetch(endpoint, {
        method: "POST",
        body: JSON.stringify({
          "model": payload.model,
          "messages": [{
            "role": "user",
            "content": payload.prompt
          }]
        }),
        headers: {
          Authorization: `Bearer ${rossum_authorization_token}`,
          "Content-Type": "application/json",
        },
      });
      const body = await response.json();
      
      console.log(body);
      return {
        messages: [{
          type: "info",
          content: body.messages.find(message => message.role === "system").content,
          id: "all",
        }]
      }
    }
    catch (e) {
      return {
        messages: [{
          type: "error",
          content: `${e.message}, ${JSON.stringify(payloads)}`,
          id: "all",
        }]
      }
    }
  }
};