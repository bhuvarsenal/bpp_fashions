kubectl get service
POD_NAME=$(kubectl get pod -l app=flask -o jsonpath="{.items[0].metadata.name}")
kubectl exec $POD_NAME --stdin -- pytest