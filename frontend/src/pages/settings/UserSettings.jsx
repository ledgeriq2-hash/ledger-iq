import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import Card from "../../components/ui/Card.jsx";
import Input from "../../components/ui/Input.jsx";
import Button from "../../components/ui/Button.jsx";

const UserSettings = () => {
  return (
    <MainLayout>
      <Card title="Profile">
        <Input label="Full name" placeholder="Your name" />
        <Input label="Email" placeholder="you@example.com" />
        <Button style={{ marginTop: "0.75rem" }}>Save</Button>
      </Card>
    </MainLayout>
  );
};

export default UserSettings;
