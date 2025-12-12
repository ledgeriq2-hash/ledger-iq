import React from "react";
import Banner from "./Banner.jsx";

const ErrorBox = ({ title = "Something went wrong", message }) => (
  <Banner title={title} message={message} variant="danger" />
);

export default ErrorBox;
