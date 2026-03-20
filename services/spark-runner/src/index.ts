import "dotenv/config";
import express from "express";
import cors from "cors";
import { sparkContextRouter } from "./routes/spark-context.js";

const app = express();
const PORT = process.env.PORT || 8001;

// Middleware
app.use(cors());
app.use(express.json());

// Auth middleware
const authMiddleware = (
  req: express.Request,
  res: express.Response,
  next: express.NextFunction
) => {
  const authHeader = req.headers.authorization;
  const expectedSecret = process.env.RUNNER_SECRET;

  if (!expectedSecret) {
    console.warn("RUNNER_SECRET not set - auth disabled");
    return next();
  }

  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return res.status(401).json({ error: "Missing authorization header" });
  }

  const token = authHeader.slice(7);
  if (token !== expectedSecret) {
    return res.status(401).json({ error: "Invalid authorization token" });
  }

  next();
};

// Health check (no auth required)
app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "spark-runner" });
});

// API routes (auth required)
app.use("/api", authMiddleware, sparkContextRouter);

// Error handler
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error("Unhandled error:", err);
  res.status(500).json({ error: err.message || "Internal server error" });
});

app.listen(PORT, () => {
  console.log(`Spark Runner listening on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});
