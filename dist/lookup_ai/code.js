const fstring = {
  oneOf: [
    {
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
  payload,
  base_url,
  rossum_authorization_token,
}) => {
  if (configure === true) {
    return {
      intent: {
        form: {
          uiSchema: {
            type: "VerticalLayout",
            elements: [
              {
                type: "FString",
                scope: "#/properties/prompt",
              },
            ],
          },
          schema: {
            definitions: {
              fstring,
            },
            type: "object",
            properties: {
              prompt: {
                $ref: "#/definitions/fstring",
              },
            },
          },
        },
      },
    };
  } else {
    const endpoint = `${base_url}/api/v1/internal/chatbot`;
    const response = await fetch(endpoint, {
      method: "POST",
      body: JSON.stringify({
        model: "anthropic.claude-v2",
        messages: [
          {
            role: "user",
            content: `${payload.prompt}. Separate each entry with comma. Do not add any additional text.`,
          },
        ],
      }),
      headers: {
        Authorization: `Bearer ${rossum_authorization_token}`,
        "Content-Type": "application/json",
      },
    });
    const body = await response.json();
    const options = body.messages
      .find((message) => message.role === "system")
      .content.split(",").map(option => ({ label: option, value: option }));

    return {
      options,
      value: options[0],
    };
  }
};
