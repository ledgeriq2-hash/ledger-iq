import { useContext } from "react";
import { NotificationContext } from "../contexts/NotificationContext.jsx";

const useNotifications = () => useContext(NotificationContext);

export default useNotifications;
