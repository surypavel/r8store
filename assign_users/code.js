const toId = (url) => {
  const regex = /queues\/(\d+)/;
  return url.match(regex)?.[1];
}

// You can use false for testing purposes
commit = true

exports.rossum_hook_request_handler = async ({
  rossum_authorization_token,
  form,
  location,
  base_url,
  hook,
}) => {

  const queueId = toId(form?.queue ?? '') ?? toId(location.pathname)

  if (queueId && form?.users) {
    const response = await fetch(`${base_url}/api/v1/queues/${queueId}`, {
      method: "GET",
      headers: {
        "Authorization": `Token ${rossum_authorization_token}`
      }
    })

    const data = await response.json();

    const success = commit ? await fetch(`${base_url}/api/v1/queues/${queueId}`, {
      method: "PATCH",
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        "Authorization": `Token ${rossum_authorization_token}`
      },
      body: JSON.stringify({
        users: [...data.users, ...form?.users.map(user => user.url)]
      })
    }).then(mutation => mutation.status === 200) : true

    if (success) {
      return {
        intent: {
          info: {
            message: `Users were successfully added to queue: ${data.name}.`
          },
          form: null,
          redirect: {
            url: `/queues/${data.id}/settings/access`
          }
        }
      };
    }
    return {
      intent: {
        error: {
          message: `Something went wrong.`
        },
      }
    };
  }

  if (queueId) {
    const response = await fetch(`${base_url}/api/v1/users?page_size=200&deleted=false&groups=2`, {
      method: "GET",
      headers: {
        "Authorization": `Token ${rossum_authorization_token}`
      }
    })

    const data = await response.json();
    const usersToAssign = data.results.filter(user => !user.queues.map(queue => toId(queue)).includes(queueId));

    return usersToAssign.length ? {
      intent: {
        form: {
          width: 1000,
          hook,
          defaultValue: {
            queue: `queues/${queueId}`,
            users: usersToAssign.map(result => ({
              email: result.email || result.username,
              name: `${result.first_name} ${result.last_name}`,
              url: result.url
            }))
          },
          uiSchema: {
            "type": "Group",
            "label": "I will be assigning the following users to the queue:",
            "elements": [{
              "type": "Control",
              "scope": "#/properties/users",
              "options": {
                "elementLabelProp": "email",
                "add": false,
                "detail": {
                  "type": "VerticalLayout",
                  "elements": [{
                      "type": "Control",
                      "scope": "#/properties/email",
                      "options": {
                        readonly: true
                      }
                    },
                    {
                      "type": "Control",
                      "scope": "#/properties/name",
                      "options": {
                        readonly: true
                      }
                    }
                  ]
                }
              }
            }]
          },
          schema: {
            type: "object",
            properties: {
              "users": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "email": {
                      "type": "string",
                    },
                    "name": {
                      "type": "string",
                    }
                  }
                }
              }
            }
          }
        }
      }
    } : {
      intent: {
        error: {
          message: "All annotators are assigned to this queue."
        }
      }
    }
  }

  return {
    intent: {
      form: {
        width: 500,
        hook,
        schema: {
          type: 'object',
          properties: {
            queue: {
              type: 'string'
            },
          },
          required: ['queue'],
        },
        uiSchema: {
          "type": "Group",
          "label": "Please select the queue first",
          "elements": [{
            type: 'Control',
            scope: '#/properties/queue',
          }, ]
        }
      }
    }
  };
};
