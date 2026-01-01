import { createBrowserRouter } from "react-router-dom";
import routes from "./routes/index.jsx";

const router = createBrowserRouter(routes, {
  future: {
    v7_startTransition: true,
  },
});

export default router;
