const node_fetch = require("node-fetch");

const getConfigureIntent = () => {
  return {
    intent: {
      form: {
        width: 500,
        schema: {
          type: "object",
          properties: {
            annotation: {
              type: "string",
            },
          },
          required: ["annotation"],
        },
        uiSchema: {
          type: "VerticalLayout",
          elements: [
            {
              label: "Target annotation ID",
              type: "Control",
              scope: "#/properties/annotation",
            },
          ],
        },
      },
    },
  };
};

exports.rossum_hook_request_handler = async ({
  rossum_authorization_token,
  base_url,
  ui_action,
  payload,
  annotation,
}) => {
  if (ui_action === "configure") {
    return getConfigureIntent();
  } else {
    const targetAnnotation = await node_fetch(
      `${base_url}/api/v1/annotations/${payload.annotation}`,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          Authorization: `Token ${rossum_authorization_token}`,
        },
      }
    ).then((targetAnnotation) => targetAnnotation.json());

    const sourceAnnotation = await node_fetch(
      `${base_url}/api/v1/annotations/${annotation.id}`,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          Authorization: `Token ${rossum_authorization_token}`,
        },
      }
    ).then((sourceAnnotation) => sourceAnnotation.json());

    return await node_fetch(`${base_url}/api/v1/relations`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Authorization: `Token ${rossum_authorization_token}`,
      },
      body: JSON.stringify({
        type: "attachment",
        parent: sourceAnnotation.url,
        annotations: [targetAnnotation.url],
      }),
    }).then(async (mutation) => {
      const message = JSON.stringify(await mutation.json());
      return mutation.status === 200
        ? {
            intent: {
              success: { message: "Annotation was attached successfully." },
            },
          }
        : { intent: { error: { message: message } } };
    });
  }
};
