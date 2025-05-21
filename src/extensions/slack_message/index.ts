import { sendSlackMessage } from "./util";

type ServerlessFnProps = {
  settings: Record<string, unknown>;
  secrets: Record<string, unknown>;
  configure: boolean;
  annotation: { id: number };
  payloads: Array<{ message: string }>;
};

export const rossum_hook_request_handler = async ({
  settings,
  secrets,
  payloads,
  annotation,
  configure,
}: ServerlessFnProps) => {
  if (configure === true) {
    return {
      intent: {
        form: {
          uiSchema: {
            type: "VerticalLayout",
            elements: {
              type: "FString",
              scope: `#/properties/message`,
            },
          },
          schema: {
            type: "object",
            properties: {
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
    const sendMessage = async (message: string) => {
      await sendSlackMessage(secrets.token, message, settings.channel_id);
    };

    try {
      await sendMessage(
        `You are getting messages from annotation ${
          annotation.id
        }: \n\n ${payloads
          .map((payload) => `* ${payload.message}`)
          .join("\n ")}`
      );

      return {
        messages: [{ type: "info", content: "Message was sent successfully." }],
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
