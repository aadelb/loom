# Loom Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the Loom MCP server.

## Quick Start

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Nginx Ingress Controller (optional, for ingress)
- Cert-Manager (optional, for TLS)

### Deploy

```bash
# Using kustomize
kubectl apply -k ./k8s

# Or apply individual files
kubectl apply -f k8s/
```

### Verify Deployment

```bash
kubectl get pods -n loom
kubectl logs -n loom -l app=loom-mcp
kubectl get svc -n loom
```

## Configuration

Edit these files before deployment:

- `configmap.yaml` — Service configuration (LOOM_HOST, LOG_LEVEL, etc.)
- `secret.yaml` — API keys and credentials (replace YOUR_*_HERE values)
- `ingress.yaml` — Hostname and TLS settings (update loom.example.com)

## Resource Breakdown

| Component | Type | Replicas | CPU | Memory |
|-----------|------|----------|-----|--------|
| loom-server | Deployment | 2-8 (HPA) | 500m-1000m | 512Mi-1Gi |
| loom-redis | StatefulSet | 1 | 100m-500m | 256Mi-512Mi |

## Scaling

HPA automatically scales 2-8 replicas based on:
- CPU utilization > 70%
- Memory utilization > 80%

Adjust in `hpa.yaml` if needed.

## Cleanup

```bash
kubectl delete -k ./k8s
```
