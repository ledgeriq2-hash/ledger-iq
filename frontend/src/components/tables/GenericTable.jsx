import React from "react";
import Card from "../ui/Card.jsx";
import Button from "../ui/Button.jsx";
import DataTable from "../ui/DataTable.jsx";

const GenericTable = ({ title, columns = [], data = [], actions = {} }) => {
  const hasActions = actions && (actions.onEdit || actions.onDelete);
  const allColumns = hasActions
    ? [
        ...columns,
        {
          Header: "Actions",
          accessor: "__actions",
          Cell: (_value, row) => (
            <div className="u-flex u-gap-2 u-wrap">
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
            </div>
          ),
        },
      ]
    : columns;

  return (
    <Card title={title}>
      <DataTable columns={allColumns} data={data} emptyTitle="No data" emptyMessage="Nothing to show yet." />
    </Card>
  );
};

export default GenericTable;
