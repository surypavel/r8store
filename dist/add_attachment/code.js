const getConfigureIntent = () => {
    return {
      intent: {
        form: {
          width: 500,
          hook,
          schema: {
            type: 'object',
            properties: {
              annotation: {
                type: 'string'
              },
            },
            required: ['annotation'],
          },
          uiSchema: {
            "type": "VerticalLayout",
            "label": "Target annotation ID",
            "elements": [{
              type: 'Control',
              scope: '#/properties/annotation',
            }, ]
          }
        }
      }
    };
  }
  
  exports.rossum_hook_request_handler = async ({
    rossum_authorization_token,
    base_url,
    action
  }) => {
    if (action === "configure") {
      return getConfigureIntent();
    } else {
      return await fetch(`${base_url}/api/v1/relations`, {
        method: "POST",
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          "Authorization": `Token ${rossum_authorization_token}`
        },
        body: JSON.stringify({
          "type": "attachment",
          "parent": "https://<example>.rossum.app/api/v1/annotations/123",
          "annotations": ["https://<example>.rossum.app/api/v1/annotations/124"],
        })
      }).then(async (mutation) => {
        const message = JSON.stringify(await mutation.json());
        return mutation.status === 200 ? { intent: { success: { message: "Asdf" } } } : { intent: { error: { message: message } }}
      })
    }
  };