const getIDFromUrl = (url) => Number(url.split('/').pop())

exports.rossum_hook_request_handler = async ({
  rossum_authorization_token,
  configure,
  payload,
  base_url,
  settings,
  annotation,
}) => {
  if (configure === true) {
    return {
      "intent": {
        "form": {
          "schema": {
            type: 'object',
            properties: Object.fromEntries(settings.locales.map(locale => ([locale, {
              type: 'string',
            }])))
          },
        }
      }
    }
  } else {
    const endpoint = `${base_url}/api/v1/users/${getIDFromUrl(annotation.modified_by)}`;
    const response = await fetch(endpoint, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${rossum_authorization_token}`
      }
    });

    const user = await response.json();
    const content = payload[user.ui_settings.locale];

    // Do stuff with payload and rossum token and annotation.
    return content ? {
      "messages": [{
        type: "warning",
        content,
        id: "all"
      }]
    } : undefined
  }
};