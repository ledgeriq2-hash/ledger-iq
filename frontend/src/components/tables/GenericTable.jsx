import React from "react";
import Card from "../ui/Card.jsx";
import Button from "../ui/Button.jsx";

const GenericTable = ({ title, columns = [], data = [], actions = {} }) => {
  const hasActions = actions && (actions.onEdit || actions.onDelete);
  const allColumns = hasActions ? [...columns, { Header: "Actions", accessor: "__actions" }] : columns;

  return (
    <Card title={title}>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {allColumns.map((col) => (
                <th
                  key={col.accessor}
                  style={{ textAlign: "left", padding: "0.65rem", background: "#f8fafc", color: "#0f172a" }}
                >
                  {col.Header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.length === 0 && (
              <tr>
                <td colSpan={allColumns.length} style={{ padding: "0.75rem", color: "#94a3b8" }}>
                  No data
                </td>
              </tr>
            )}
            {data.map((row, idx) => (
              <tr key={idx} style={{ borderTop: "1px solid #e2e8f0" }}>
                {allColumns.map((col) => {
                  if (col.accessor === "__actions") {
                    return (
                      <td key={`actions-${idx}`} style={{ padding: "0.65rem", display: "flex", gap: "0.35rem" }}>
                        {actions.onEdit && (
                          <Button size="sm" variant="ghost" onClick={() => actions.onEdit(row)}>
                            Edit
                          </Button>
                        )}
                        {actions.onDelete && (
                          <Button size="sm" variant="ghost" onClick={() => actions.onDelete(row)}>
                            Delete
                          </Button>
                        )}
                      </td>
                    );
                  }
                  return (
                    <td key={col.accessor} style={{ padding: "0.65rem", color: "#0f172a" }}>
                      {col.Cell ? col.Cell(row[col.accessor], row) : row[col.accessor]}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

export default GenericTable;
