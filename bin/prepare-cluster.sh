#!/usr/bin/env bash
set -euo pipefail
oc whoami >/dev/null

# The integration tests use a separate database so they cannot erase live accounts.
for db_service in postgresql accounts-test-db; do
  if [[ "$db_service" == postgresql ]]; then secret=accounts-database; else secret=accounts-test-database; fi
  if ! oc get secret "$secret" >/dev/null 2>&1; then
    db_password=$(openssl rand -hex 16)
    oc create secret generic "$secret" \
      --from-literal=POSTGRESQL_USER=accounts \
      --from-literal=POSTGRESQL_PASSWORD="$db_password" \
      --from-literal=POSTGRESQL_DATABASE=accounts \
      --from-literal=DATABASE_URI="postgresql://accounts:${db_password}@${db_service}:5432/accounts"
  fi
  cat <<EOF | oc apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${db_service}
spec:
  replicas: 1
  selector:
    matchLabels: {app: ${db_service}}
  template:
    metadata:
      labels: {app: ${db_service}}
    spec:
      containers:
      - name: postgresql
        image: image-registry.openshift-image-registry.svc:5000/openshift/postgresql:15-el8
        envFrom:
        - secretRef: {name: ${secret}}
        ports:
        - containerPort: 5432
        resources:
          requests: {cpu: 50m, memory: 128Mi}
          limits: {cpu: 300m, memory: 256Mi}
        volumeMounts:
        - {name: data, mountPath: /var/lib/pgsql/data}
        readinessProbe:
          tcpSocket: {port: 5432}
          initialDelaySeconds: 5
      volumes:
      - name: data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: ${db_service}
spec:
  selector: {app: ${db_service}}
  ports:
  - {port: 5432, targetPort: 5432}
EOF
done
oc rollout status deployment/postgresql --timeout=180s
oc rollout status deployment/accounts-test-db --timeout=180s
oc get imagestream accounts >/dev/null 2>&1 || oc create imagestream accounts
oc apply -f tekton/pvc.yaml
