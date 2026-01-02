import React from "react";
import EmptyState from "./EmptyState.jsx";
import Skeleton from "./Skeleton.jsx";

const normalizeColumns = (columns) =>
  (columns || []).map((col) => ({
    key: col.accessor || col.key || col.Header || col.header,
    header: col.Header ?? col.header ?? "",
    accessor: col.accessor ?? col.key,
    cell: col.Cell ?? col.cell,
    align: col.align,
    width: col.width,
  }));

const DataTable = ({
  columns = [],
  data = [],
  loading = false,
  emptyTitle,
  emptyMessage,
  emptyAction,
  rowKey,
  onRowClick,
}) => {
  const cols = normalizeColumns(columns);
  const resolvedRowKey = rowKey || ((row, idx) => row?.id ?? row?.key ?? idx);

  const isEmpty = !loading && (!data || data.length === 0);

  return (
    <div className="tableScroll">
      <table className="kit-table">
        <colgroup>
          {cols.map((col) => (
            <col key={col.key} width={col.width || undefined} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {cols.map((col) => (
              <th
                key={col.key}
                className={`tableAlign-${col.align === "center" ? "center" : col.align === "right" ? "end" : "start"}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading &&
            Array.from({ length: 5 }).map((_, idx) => (
              <tr key={`sk-${idx}`} className="kit-tableRow">
                {cols.map((col) => (
                  <td key={`${col.key}-sk-${idx}`}>
                    <Skeleton className="kit-skeletonLine" />
                  </td>
                ))}
              </tr>
            ))}

          {isEmpty && (
            <tr>
              <td colSpan={Math.max(cols.length, 1)} className="kit-tableEmptyCell">
                <EmptyState
                  compact
                  title={emptyTitle || "No data"}
                  message={emptyMessage || "Nothing to show yet."}
                  action={emptyAction}
                />
              </td>
            </tr>
          )}

          {!loading &&
            (data || []).map((row, idx) => {
              const key = resolvedRowKey(row, idx);
              const clickable = typeof onRowClick === "function";
              return (
                <tr
                  key={key}
                  className="kit-tableRow"
                  data-clickable={clickable ? "true" : "false"}
                  onClick={clickable ? () => onRowClick(row) : undefined}
                >
                  {cols.map((col) => {
                    const value = col.accessor ? row?.[col.accessor] : undefined;
                    return (
                      <td
                        key={`${key}-${col.key}`}
                        className={`tableAlign-${col.align === "center" ? "center" : col.align === "right" ? "end" : "start"}`}
                      >
                        {col.cell ? col.cell(value, row) : value ?? ""}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
        </tbody>
      </table>
    </div>
  );
};

export default DataTable;
