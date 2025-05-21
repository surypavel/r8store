const getIDFromUrl = (url) => Number(url.split("/").pop());

exports.rossum_hook_request_handler = async ({
  rossum_authorization_token,
  configure,
  payloads,
  base_url,
  settings,
  annotation,
}) => {
  if (configure === true) {
    return {
      intent: {
        form: {
          uiSchema: {
            type: "VerticalLayout",
            elements: settings.locales.map((locale) => ({
              type: "FString",
              scope: `#/properties/${locale}`,
            })),
          },
          schema: {
            type: "object",
            properties: Object.fromEntries(
              settings.locales.map((locale) => [
                locale,
                {
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
              ])
            ),
          },
        },
      },
    };
  } else {
    const endpoint = `${base_url}/api/v1/users/${getIDFromUrl(
      annotation.modified_by
    )}`;
    const response = await fetch(endpoint, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${rossum_authorization_token}`,
      },
    });

    const user = await response.json();

    return {
      messages: payloads.flatMap((payload) => {
        const defaultLocale = "en";
        const content = payload[user.ui_settings.locale ?? defaultLocale];

        // Do stuff with payload and rossum token and annotation.
        return content
          ? [
              {
                type: "warning",
                content,
                id: "all",
              },
            ]
          : [];
      }),
    };
  }
};
