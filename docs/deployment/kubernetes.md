# Kubernetes Deployment

Deploy Loom to Kubernetes for orchestrated, auto-healing containerized workloads. This guide covers when to use k8s and how to apply the provided manifests.

## When to Use Kubernetes

Kubernetes is useful if you already operate k8s (EKS, AKS, GKE, self-hosted) and want:

- **Self-healing** — Pod restarts on failure (liveness probes)
- **Orchestration** — Declarative, version-controlled infrastructure
- **Resource quotas** — CPU/memory limits, requests, namespace isolation
- **ConfigMaps/Secrets** — Centralized config and secret management

**Not recommended if:**

- You want a simple single-machine setup → use **systemd** or **Docker**
- You're just testing Loom locally → use **Docker or pip install**
- You're uncomfortable with k8s administration → use **Docker Compose**

Loom stores browser sessions in a PersistentVolume, so it does not scale horizontally (multiple replicas reuse the same sessions, which breaks session isolation). **Keep replicas = 1**.

## Quick Start

Clone the repo and apply the example manifests:

```bash
git clone https://github.com/aadelb/loom.git
cd loom

# Create namespace and apply all resources
kubectl apply -f deploy/kubernetes/deployment.yaml.example
```

This creates:

- **Namespace:** `loom` (isolated from other workloads)
- **ConfigMap:** `loom-config` (non-secret env vars: LOOM_HOST, SPIDER_CONCURRENCY, etc.)
- **Secret:** `loom-api-keys` (API keys for search and LLM providers)
- **PersistentVolumeClaim:** `loom-data` (50 GB volume for cache, logs, sessions)
- **Deployment:** `loom` (single-replica pod)
- **Service:** `loom` (ClusterIP, port 8787)
- **PodDisruptionBudget:** ensures the pod is not evicted during maintenance

## Configuration

### 1. Edit the Secret

The example file includes placeholder API keys. Replace them:

```bash
kubectl edit secret loom-api-keys -n loom
```

Or patch individual keys:

```bash
kubectl patch secret loom-api-keys -n loom \
  --type json \
  -p='[{"op": "replace", "path": "/data/NVIDIA_NIM_API_KEY", "value":"'$(echo -n 'your_key' | base64)'"}]'
```

### 2. Adjust Resource Requests/Limits

The default manifest requests 2 CPU cores and 4 GB RAM. Adjust based on your cluster:

```bash
kubectl edit deployment loom -n loom
```

```yaml
resources:
  requests:
    cpu: 1000m        # Request 1 CPU
    memory: 2Gi       # Request 2 GB RAM
  limits:
    cpu: 4000m        # Hard cap at 4 CPU
    memory: 16Gi      # Hard cap at 16 GB
```

### 3. PersistentVolume Sizing

The default PVC requests 50 GB. Increase if you plan heavy caching:

```bash
kubectl patch pvc loom-data -n loom \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/resources/requests/storage", "value":"100Gi"}]'
```

Then scale the PV backing it.

### 4. ConfigMap

Non-secret config lives in `loom-config`. Edit to tune:

```bash
kubectl edit cm loom-config -n loom
```

Available keys (same as `docs/tools/research_config.md`):

- `SPIDER_CONCURRENCY` (default: 5, range 1–20)
- `LOOM_LOG_LEVEL` (INFO, DEBUG, WARNING, ERROR)
- `LLM_PROVIDER_CASCADE` (comma-separated, e.g., "nvidia,openai")
- etc.

## Health Checks

The deployment includes liveness and readiness probes that ping the MCP initialize endpoint:

```yaml
livenessProbe:
  httpProbe:
    path: /mcp
    port: mcp
  initialDelaySeconds: 60        # Wait 60s before first probe
  periodSeconds: 30              # Check every 30s
  failureThreshold: 3            # Restart after 3 consecutive failures

readinessProbe:
  httpProbe:
    path: /mcp
    port: mcp
  initialDelaySeconds: 30        # Wait 30s before first probe
  periodSeconds: 10              # Check every 10s
  failureThreshold: 2            # Remove from LB after 2 failures
```

If Loom is unresponsive, the pod will restart automatically.

## Networking

The service is `ClusterIP`, meaning it's only accessible within the cluster. To access from your machine:

```bash
# Port-forward to localhost:8787
kubectl port-forward -n loom svc/loom 8787:8787
```

Then use Claude Code with `http://127.0.0.1:8787/mcp`.

To expose outside the cluster, change the service type:

```bash
kubectl patch service loom -n loom -p '{"spec":{"type":"LoadBalancer"}}'
```

This creates a load balancer (cloud-specific). Verify:

```bash
kubectl get svc loom -n loom
```

**Warning:** LoadBalancer exposes the MCP endpoint to the internet. Add authentication (via reverse proxy) before doing this.

## Persistence

The PVC `loom-data` is mounted at `/data` in the pod. The deployment sets:

```yaml
volumeMounts:
  - name: data
    mountPath: /data
```

And environment variables point to `/data/cache`, `/data/logs`, `/data/sessions`. These directories are shared across pod restarts (StatefulSet would be needed for per-pod persistence, which Loom doesn't use).

## Single-Replica Guarantee

The PodDisruptionBudget ensures the single pod is not evicted:

```yaml
podDisruptionBudget:
  minAvailable: 1
```

If you try to scale the deployment to 2+ replicas, they will share the same PVC, causing session collisions. Don't do this.

## Deployment Updates

To update the image (e.g., to a new version):

```bash
kubectl set image deployment/loom -n loom \
  loom=ghcr.io/aadelb/loom:v0.2.0
```

Or edit the deployment:

```bash
kubectl set image deployment/loom -n loom \
  loom=ghcr.io/aadelb/loom:latest \
  --record
```

Rolling update happens automatically; the pod gracefully shuts down (30-second termination grace period) and a new one starts.

## Troubleshooting

### Pod doesn't start

Check pod status:

```bash
kubectl describe pod -n loom -l app=loom
```

Look for "Events" at the bottom. Common issues:

- **Image pull error** — Wrong image or no permission to pull from ghcr.io
- **PVC not bound** — Storage class doesn't exist or PV provisioning failed
- **Pending (waiting for node)** — Cluster doesn't have enough resources

### Liveness probe failing

```bash
kubectl logs -n loom -l app=loom -f
```

Check if Loom is actually running:

```bash
kubectl exec -it -n loom -l app=loom -- curl -X POST http://127.0.0.1:8787/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}'
```

If Loom is unresponsive but the container is running, check logs and increase `initialDelaySeconds` in the probe.

### High memory usage

Reduce `SPIDER_CONCURRENCY`:

```bash
kubectl set env deployment/loom -n loom SPIDER_CONCURRENCY=2
```

Or increase the pod limit:

```bash
kubectl patch deployment loom -n loom \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"loom","resources":{"limits":{"memory":"32Gi"}}}]}}}}'
```

### PVC full

Check usage:

```bash
kubectl exec -n loom -l app=loom -- df -h /data
```

Increase PVC size (if your storage class allows online expansion):

```bash
kubectl patch pvc loom-data -n loom \
  -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'
```

## Example: Accessing from Claude Code

1. Port-forward to localhost:

```bash
kubectl port-forward -n loom svc/loom 8787:8787
```

2. Update `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "loom": {
      "type": "http",
      "url": "http://127.0.0.1:8787/mcp"
    }
  }
}
```

3. Restart Claude Code. Loom's 23 tools should appear.

## Optional: Horizontal Pod Autoscaler

The example manifest includes a commented-out HPA. **Do not use this** because sessions are not shared across replicas. If you uncomment it, pods will scale on CPU usage, breaking session isolation.

To use it anyway (at your own risk), first enable metrics-server:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

Then uncomment and apply the HPA from the manifest. This will scale Loom to 1–3 replicas based on CPU.

## Cleanup

Delete all Loom resources:

```bash
kubectl delete namespace loom
```

This removes the namespace, deployments, services, configmaps, secrets, and PVC.

## Related Documentation

- [docs/installation.md](../installation.md) — Installation options
- [docs/deployment/docker.md](docker.md) — Docker deployment
- [docs/deployment/systemd.md](systemd.md) — systemd service
- [docs/deployment/claude-code-integration.md](claude-code-integration.md) — Claude Code setup
