const toId = (url) => {
    const regex = /document\/(\d+)/;
    return url.match(regex)?.[1];
  }
  
  const flattenContent = (content, parentId = 0) => content.flatMap(el => 'children' in el ? [{
    ...el,
    parentId
  }, flattenContent(el.children, el.id)] : {
    ...el,
    parentId
  }).flat()
  
  exports.rossum_hook_request_handler = async ({
    settings,
    location,
    base_url,
    rossum_authorization_token,
    form,
  }) => {
    const annotationId = toId(location.pathname);
  
    if (!annotationId) return {
      intent: {
        error: {
          message: "You need to be on the annotation view to run this command."
        }
      }
    }
  
    const endpoint = `${base_url}/api/v1/annotations/${annotationId}/content`
  
    const response = await fetch(endpoint, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${rossum_authorization_token}`
      }
    })
  
    const result = await response.json()
  
    if (!result.content) return {
      intent: {
        error: {
          message: "Failed to fetch the content of this annotation."
        }
      },
      data: result,
      token: rossum_authorization_token ?? 'n/a'
    }
  
    const normalized = flattenContent(result.content)
  
    const list = normalized.map(item => ({
      schemaId: item.schema_id ?? 'N/A',
      id: item.id,
      category: item.category,
      parentId: item.parentId
    })) ?? []
  
    const filteredList = form && form.search ? list.filter(item => item.id == form.search) : list;
  
    return {
      intent: {
        form: {
          width: 600,
          defaultValue: {
            table: filteredList,
            title: {
              text: "Document datapoints"
            }
          },
          uiSchema: {
            "type": "Group",
            "elements": [{
              "type": "Typography",
              "options": {
                variant: "h5",
                sx: {
                  mb: 2
                }
              },
              "scope": '#/properties/title'
            }, {
              "type": "Table",
              "scope": '#/properties/table'
            }]
          },
        }
      },
      result,
    };
  };