# Kubernetes Deployment Guide for Loom

This directory contains Kubernetes manifests for deploying Loom as a containerized service.

## Prerequisites

- Kubernetes cluster 1.20+ (with persistent volumes support)
- kubectl configured to access your cluster
- Persistent volume provisioner (StorageClass) available
- Container registry access (GHCR or private registry)

## Quick Start

### 1. Prepare Secrets

Create a file `kube-loom-secrets.yaml` with your API keys:

```bash
cat > kube-loom-secrets.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: loom-api-keys
  namespace: loom
type: Opaque
stringData:
  EXA_API_KEY: "YOUR_KEY_HERE"
  TAVILY_API_KEY: "YOUR_KEY_HERE"
  FIRECRAWL_API_KEY: "YOUR_KEY_HERE"
  BRAVE_API_KEY: "YOUR_KEY_HERE"
  NVIDIA_NIM_API_KEY: "YOUR_KEY_HERE"
  OPENAI_API_KEY: "YOUR_KEY_HERE"
  ANTHROPIC_API_KEY: "YOUR_KEY_HERE"
EOF
```

### 2. Deploy

```bash
# Deploy the manifest
kubectl apply -f deploy/kubernetes/deployment.yaml.example

# Apply your secret (from step 1)
kubectl apply -f kube-loom-secrets.yaml

# OR use kustomize with a secret generator:
# kustomize edit add secret loom-api-keys --from-env-file=.env.prod
# kubectl apply -k .
```

### 3. Verify

```bash
# Check pod status
kubectl get pods -n loom
kubectl describe pod -n loom -l app=loom

# View logs
kubectl logs -n loom -l app=loom -f

# Port-forward to test
kubectl port-forward -n loom svc/loom 8787:8787

# Test the MCP endpoint
curl -X POST http://127.0.0.1:8787/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"initialize",
    "params":{
      "protocolVersion":"2024-11-05",
      "capabilities":{},
      "clientInfo":{"name":"test","version":"1"}
    }
  }'
```

## Deployment Manifest Overview

The `deployment.yaml.example` includes:

### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: loom
```

Creates an isolated namespace for Loom resources.

### ConfigMap

Stores non-sensitive configuration:

```yaml
LOOM_HOST: "0.0.0.0"
LOOM_PORT: "8787"
SPIDER_CONCURRENCY: "5"
LLM_PROVIDER_CASCADE: "nvidia,openai"
```

Update these values based on your deployment requirements.

### Secret

Stores sensitive credentials. **IMPORTANT:** Do NOT commit actual keys to version control. Use one of:

- **Option 1:** Manual secret creation (recommended for production)
  ```bash
  kubectl create secret generic loom-api-keys -n loom \
    --from-literal=EXA_API_KEY=$EXA_API_KEY \
    --from-literal=OPENAI_API_KEY=$OPENAI_API_KEY \
    ... (other keys)
  ```

- **Option 2:** Sealed Secrets (for GitOps)
  ```bash
  kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml
  echo -n $OPENAI_API_KEY | kubectl create secret generic loom-api-keys \
    --dry-run=client --from-file=OPENAI_API_KEY=/dev/stdin -o yaml | \
    kubeseal -f - > loom-api-keys-sealed.yaml
  ```

- **Option 3:** External Secrets Operator
  ```bash
  # Connect to HashiCorp Vault, AWS Secrets Manager, etc.
  ```

### PersistentVolumeClaim

Allocates 50 GB for cache, logs, and session data:

```yaml
spec:
  resources:
    requests:
      storage: 50Gi
```

Adjust based on expected cache size. Typical usage:

- Cache: 1-5 GB (depends on pages scraped)
- Sessions: 100 MB (browser profiles)
- Logs: 500 MB - 2 GB (depends on log level)

### Deployment

Single-replica deployment (sessions are stateful):

```yaml
replicas: 1
```

**Note:** Loom stores browser sessions locally. Running multiple replicas requires shared storage or session migration logic.

Resource specifications:

```yaml
resources:
  requests:
    cpu: 2000m       # 2 CPU cores
    memory: 4Gi      # 4 GB RAM
  limits:
    cpu: 4000m       # Max 4 cores
    memory: 16Gi     # Max 16 GB
```

Adjust based on your workload and cluster capacity.

### Health Checks

**Liveness Probe:** Restarts unhealthy pods

```yaml
livenessProbe:
  httpProbe:
    path: /mcp
    port: 8787
  initialDelaySeconds: 60   # Wait 60s before first check
  periodSeconds: 30         # Check every 30s
  failureThreshold: 3       # Restart after 3 failures
```

**Readiness Probe:** Removes unhealthy pods from load balancer

```yaml
readinessProbe:
  httpProbe:
    path: /mcp
    port: 8787
  initialDelaySeconds: 30   # Wait 30s before first check
  periodSeconds: 10         # Check every 10s
  failureThreshold: 2       # Remove after 2 failures
```

### Service

Exposes Loom within the cluster:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: loom
  namespace: loom
spec:
  type: ClusterIP
  selector:
    app: loom
  ports:
    - name: mcp
      port: 8787
      targetPort: 8787
```

Access from within the cluster:

```
http://loom.loom.svc.cluster.local:8787/mcp
```

For external access, use:

- **LoadBalancer:** `kubectl patch svc loom -n loom -p '{"spec":{"type":"LoadBalancer"}}'`
- **NodePort:** Change `type: ClusterIP` to `type: NodePort`
- **Ingress:** Create an Ingress resource (see below)

### Pod Disruption Budget

Ensures at least 1 pod is always available:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: loom
  namespace: loom
spec:
  minAvailable: 1
```

Protects against cluster scaling or node drains.

## Advanced Configurations

### Exposing via Ingress

Create an Ingress for TLS and authentication:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: loom
  namespace: loom
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - loom.example.com
      secretName: loom-tls
  rules:
    - host: loom.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: loom
                port:
                  name: mcp
```

### Using Private Container Registry

If using a private registry (e.g., private GHCR):

```bash
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_USERNAME \
  --docker-password=YOUR_TOKEN \
  -n loom

# Add to deployment imagePullSecrets:
# imagePullSecrets:
#   - name: ghcr-secret
```

### Running Multiple Instances

For high availability with shared sessions (requires Redis or similar):

```yaml
replicas: 3
# Add sessionAffinity: ClientIP to maintain session routing
sessionAffinity: ClientIP
sessionAffinityConfig:
  clientIP:
    timeoutSeconds: 10800
```

Then configure Loom to use shared session storage (future enhancement).

### Horizontal Pod Autoscaling

Uncomment the HPA section in `deployment.yaml.example`:

```bash
# First, install metrics-server if not present
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify metrics are available (wait ~1 min)
kubectl get hpa -n loom
```

### Using Kustomize

Organize overlays for different environments:

```
kustomize/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   ├── configmap.yaml
│   │   └── kustomization.yaml
│   ├── staging/
│   │   └── ...
│   └── prod/
│       └── ...
```

Deploy:

```bash
kubectl apply -k kustomize/overlays/prod
```

## Managing Loom in Kubernetes

### View Status

```bash
# Check pod status
kubectl get pods -n loom

# Detailed pod info
kubectl describe pod -n loom -l app=loom

# Watch events
kubectl get events -n loom --sort-by='.lastTimestamp'
```

### View Logs

```bash
# Follow logs
kubectl logs -n loom -l app=loom -f

# View previous logs (if pod crashed)
kubectl logs -n loom -l app=loom --previous

# Show last 100 lines
kubectl logs -n loom -l app=loom --tail=100

# Grep for errors
kubectl logs -n loom -l app=loom | grep ERROR
```

### Access the Service

```bash
# Port-forward from your local machine
kubectl port-forward -n loom svc/loom 8787:8787

# Then access at http://127.0.0.1:8787/mcp
```

### Update Configuration

```bash
# Edit ConfigMap
kubectl edit configmap loom-config -n loom
# Pod will need restart for changes to take effect
kubectl rollout restart deployment loom -n loom

# Update Secret
kubectl patch secret loom-api-keys -n loom \
  -p '{"data":{"EXA_API_KEY":"'$(echo -n newkey | base64)'"}}'
kubectl rollout restart deployment loom -n loom
```

### Update Image

```bash
# Force pull latest image
kubectl set image deployment/loom -n loom \
  loom=ghcr.io/aadelb/loom:v0.1.0 \
  --record

# Check rollout status
kubectl rollout status deployment/loom -n loom
```

### Troubleshooting

```bash
# Pod stuck in ImagePullBackOff
kubectl describe pod -n loom -l app=loom
# Check image name, registry credentials, network

# Pod OOMKilled (out of memory)
kubectl logs -n loom -l app=loom
kubectl describe node NODE_NAME
# Increase memory limits in deployment

# Pod not ready (readiness probe failing)
kubectl exec -n loom POD_NAME -- curl http://127.0.0.1:8787/mcp
# Check service logs, verify configuration

# PVC not bound
kubectl get pvc -n loom
kubectl describe pvc -n loom loom-data
# Check storage class, available disk space
```

### Cleanup

```bash
# Delete Loom deployment
kubectl delete deployment loom -n loom

# Delete all Loom resources
kubectl delete namespace loom

# Delete PersistentVolume (if created manually)
kubectl delete pv loom-data
```

## Production Best Practices

1. **Secrets Management:** Use HashiCorp Vault, AWS Secrets Manager, or Sealed Secrets
2. **Monitoring:** Install Prometheus + Grafana, configure alerts
3. **Logging:** Use ELK, Loki, or Datadog for centralized logging
4. **Backup:** Backup PVCs regularly (e.g., velero)
5. **Resource Quotas:** Set namespace-level resource limits
6. **Network Policies:** Restrict egress to necessary hosts only
7. **RBAC:** Create minimal-privilege service account
8. **Image Scanning:** Use Trivy, Cosign, or similar for image vulnerability scanning

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
