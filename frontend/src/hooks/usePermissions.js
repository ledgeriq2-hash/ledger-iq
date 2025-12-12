import { useMemo } from "react";
import useAuth from "./useAuth";

const usePermissions = () => {
  const { user } = useAuth();

  const roles = useMemo(() => {
    if (!user) return [];
    const collected = [];
    if (user.roles) {
      collected.push(...(Array.isArray(user.roles) ? user.roles : [user.roles]));
    }
    if (user.role) {
      collected.push(user.role.name || user.role);
    }
    if (user.role_id && collected.length === 0) {
      collected.push("owner");
    }
    if (user.is_superuser) {
      collected.push("owner", "admin");
    }
    return collected;
  }, [user]);

  const hasRole = (role) => roles.map((x) => x.toLowerCase()).includes(role.toLowerCase());

  return { roles, hasRole };
};

export default usePermissions;
