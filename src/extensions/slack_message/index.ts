import { sendSlackMessage } from "./util";

type ServerlessFnProps = {
  settings: Record<string, unknown>;
  secrets: Record<string, unknown>;
  configure: boolean;
  payload: Record<string, unknown>;
};

export const rossum_hook_request_handler = async ({
  settings,
  secrets,
  payload,
  configure,
}: ServerlessFnProps) => {
  if (configure === true) {
    return {
      intent: {
        form: {
          schema: {
            type: "object",
            properties: {
              message: {
                type: "string",
              }
            },
          },
        },
      },
    };
  } else {
    const sendMessage = async (message) => {
      await sendSlackMessage(secrets.token, message, settings.channel_id);
    };

    try {
      await sendMessage(payload.message);

      return {
        messages: [{ type: "info", content: "Message was sent successfully." }],
      };  
    } catch (error) {
      return {
        messages: [{ type: "error", content: error.message }],
      };
    }
  }
};
