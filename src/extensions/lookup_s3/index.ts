type ServerlessFnProps = {
  settings: Record<string, unknown>;
  secrets: Record<string, unknown>;
  configure: boolean;
  annotation: { id: number };
  payloads: Array<{ message: string }>;
  form: {
    dataset: string;
  };
  hook_interface: string;
  variant: string;
  payload: {
    dataset: string;
    value_key: string;
    label_key: string;
    filters: { match_key: string; value: string }[];
  };
};

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

export const rossum_hook_request_handler = async ({
  configure,
  payload,
  settings,
  variant,
  form,
  hook_interface,
}: ServerlessFnProps) => {
  const findData = async (dataset: string, filters: { match_key: string; value: string }[]) => {
    return await { results: [] };
  };

  const findDatasets = async () => {
    return await { datasets: [{ dataset_name: 'asdf' }]};
  };

  if (variant === "show_master_data") {
    if (form && form.dataset) {
      const data = await findData(form.dataset, []);

      return {
        intent: {
          form: {
            width: 600,
            defaultValue: {
              results: data.results,
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
  }

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
};
