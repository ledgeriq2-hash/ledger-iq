import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import Card from "../../components/ui/Card.jsx";
import Input from "../../components/ui/Input.jsx";
import Button from "../../components/ui/Button.jsx";

const TenantSettings = () => {
  return (
    <MainLayout>
      <Card title="Tenant Settings">
        <Input label="Tenant name" placeholder="Name" />
        <Input label="Slug" placeholder="slug" />
        <Input label="Plan" placeholder="Plan" />
        <Button style={{ marginTop: "0.75rem" }}>Save</Button>
      </Card>
    </MainLayout>
  );
};

export default TenantSettings;
