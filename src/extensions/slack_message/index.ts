import { WebClient } from "@slack/web-api";

type ServerlessFnProps = {
  settings: Record<string, unknown>;
  secrets: Record<string, unknown>;
  configure: boolean;
  annotation: { id: number };
  payloads: Array<{ message: string, blocks?: string }>;
};


const options = {};
const web = (token: string) => new WebClient(token, options);

export const sendSlackMessage = async (token: string, message: string, blocks: string, channel: string) => {
    return new Promise(async (resolve, reject) => {
        const channelId = channel;
        try {
            const response = await web(token).chat.postMessage({
                text: message,
                channel: channelId,
                blocks: JSON.parse(blocks)
            });
            return resolve(response);
        } catch (error) {
            return reject(error);
        }
    });
};

export const rossum_hook_request_handler = async ({
  settings,
  secrets,
  payloads,
  annotation,
  configure,
}: ServerlessFnProps) => {
  const secretsToken = secrets.token;
  const channelId = settings.channel_id;

  if (typeof secretsToken !== "string") {
    throw new Error("Missing token.");
  }

  if (typeof channelId !== "string") {
    throw new Error("Missing channel_id.");
  }

  if (configure === true) {
    return {
      intent: {
        form: {
          uiSchema: {
            type: "VerticalLayout",
            elements: [{
              type: "FString",
              scope: `#/properties/message`,
            }, {
              type: "Control",
              scope: `#/properties/blocks`,
              "options": {
                "multi": true
               }
            }],
          },
          schema: {
            type: "object",
            properties: {
              blocks: {
                type: 'string'
              },
              message: {
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
              },
            },
          },
        },
      },
    };
  } else {
    const sendMessage = async (message: string, blocks: string) => sendSlackMessage(secretsToken, message, blocks, channelId);

    try {
      const responses = await Promise.all(payloads.map(payload => sendMessage(
        payload.message,
        payload.blocks ?? "[]"
      )))

      return {
        messages: [{ type: "success", content: `Message was sent successfully: ${JSON.stringify(responses)}` }],
      };
    } catch (error) {
      return {
        messages: [
          {
            type: "error",
            content:
              error && typeof error == "object" && "message" in error
                ? error.message
                : "Unknown error",
          },
        ],
      };
    }
  }
};
