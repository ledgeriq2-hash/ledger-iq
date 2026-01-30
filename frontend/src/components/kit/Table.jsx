import React from "react";

const Table = ({ columns = [], rows = [], keyField = "id" }) => {
  return (
    <table className="kit-table">
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c.key}>{c.header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, idx) => (
          <tr key={row?.[keyField] || idx} className="kit-tableRow">
            {columns.map((c) => (
              <td key={c.key}>{typeof c.render === "function" ? c.render(row) : row?.[c.key]}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default Table;

