import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import Card from "../../components/ui/Card.jsx";
import Input from "../../components/ui/Input.jsx";
import Button from "../../components/ui/Button.jsx";

const SettingsAdvanced = () => {
  return (
    <MainLayout>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem" }}>
        <Card title="Tenant">
          <Input label="Name" placeholder="Tenant name" />
          <Input label="Slug" placeholder="tenant-slug" />
          <Button style={{ marginTop: "0.75rem" }}>Save</Button>
        </Card>
        <Card title="Billing">
          <Input label="Plan" placeholder="Plan" />
          <Input label="Next billing date" type="date" />
          <Button style={{ marginTop: "0.75rem" }}>Save</Button>
        </Card>
      </div>
    </MainLayout>
  );
};

export default SettingsAdvanced;
