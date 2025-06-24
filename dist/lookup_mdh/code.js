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
  secrets,
  payload,
  settings,
  variant,
  form,
  hook_interface,
}) => {
    const aggregateData = async (dataset, query) => {

    const response = await fetch(`${url}/v1/data/find`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${secrets.token}`,
      },
      body: JSON.stringify({
        find: {},
        projection: query,
        skip: 0,
        limit: 500,
        sort: {},
        dataset,
      }),
    });

    return await response.json();
  };

  const findData = async (dataset, filters) => {
    const response = await fetch(`${url}/v1/data/find`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${secrets.token}`,
      },
      body: JSON.stringify({
        find: Object.fromEntries(
          filters.map((filter) => [
            filter.match_key,
            {
              $regex: filter.value,
              $options: "i",
            },
          ])
        ),
        projection: {},
        skip: 0,
        limit: 500,
        sort: {},
        dataset,
      }),
    });

    return await response.json();
  };

  const findDatasets = async () => {
    const response = await fetch(`${url}/v2/dataset/`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${secrets.token}`,
      },
    });

    return await response.json();
  };

  const url =
    settings.url || "https://elis.master.r8.lol/svc/master-data-hub/api";

  if (variant === "command_show_master_data") {
    if (form && form.dataset) {
      const data = await findData(form.dataset, []);

      return {
        intent: {
          form: {
            width: 600,
            defaultValue: {
              results: data.results.map((result) => ({
                ...result,
                id: result._id,
              })),
            },
            uiSchema: {
              type: "Group",
              elements: [
                {
                  type: "Table",
                  scope: "#/properties/results",
                },
              ],
            },
          },
        },
      };
    }

    const datasets = await findDatasets();

    return {
      intent: {
        form: {
          hook_interface,
          schema: {
            type: "object",
            properties: {
              dataset: {
                type: "string",
                enum: datasets.datasets.map((d) => d.dataset_name),
              },
            },
          },
        },
      },
    };
  } else if (variant === "queue_lookup") {
    if (configure === true) {
      const datasets = await findDatasets();

      const columns =
        form && form.dataset
          ? Object.keys((await findData(form.dataset, [])).results[0])
          : [];

      return {
        intent: {
          form: {
            width: 600,
            uiSchema: {
              type: "VerticalLayout",
              elements: [
                {
                  type: "Control",
                  scope: "#/properties/dataset",
                },
                {
                  type: "Control",
                  scope: "#/properties/value_key",
                },
                {
                  type: "Control",
                  scope: "#/properties/label_key",
                },
                {
                  type: "Control",
                  scope: "#/properties/filters",
                  options: {
                    detail: {
                      type: "VerticalLayout",
                      elements: [
                        {
                          type: "Control",
                          scope: "#/properties/match_key",
                        },
                        {
                          type: "FString",
                          scope: "#/properties/value",
                        },
                      ],
                    },
                  },
                },
              ],
            },
            schema: {
              definitions: {
                fstring,
              },
              type: "object",
              properties: {
                dataset: {
                  type: "string",
                  enum: datasets.datasets.map((d) => d.dataset_name),
                },
                value_key: {
                  type: "string",
                  enum: columns,
                },
                label_key: {
                  type: "string",
                  enum: columns,
                },
                filters: {
                  type: "array",
                  items: {
                    type: "object",
                    properties: {
                      match_key: {
                        type: "string",
                        enum: columns,
                      },
                      value: {
                        $ref: "#/definitions/fstring",
                      },
                    },
                  },
                },
              },
            },
          },
        },
      };
    } else {
      const data = await findData(payload.dataset, payload?.filters ?? []);

      return {
        options: data.results.map((result) => ({
          value: result[payload.value_key],
          label: result[payload.label_key],
        })),
        value: data.results[0][payload.value_key],
      };
    }
  } else if (variant === "queue_lookup_aggregate") {
    if (configure === true) {
      const datasets = await findDatasets();

      return {
        intent: {
          form: {
            width: 600,
            schema: {
              type: "object",
              properties: {
                dataset: {
                  type: "string",
                  enum: datasets.datasets.map((d) => d.dataset_name),
                },
                query: {
                  type: "string",
                },
              },
            },
          },
        },
      };
    } else {
      const data = await aggregateData(payload.dataset, payload.query);

      return {
        options: data.results,
        value: data.results[0].value,
      };
    }
  }
};
