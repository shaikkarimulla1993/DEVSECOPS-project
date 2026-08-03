{{- define "vulntracker.name" -}}
vulntracker
{{- end -}}

{{- define "vulntracker.namespace" -}}
{{- if .Values.namespace.create -}}
{{ .Values.namespace.name }}
{{- else -}}
{{ .Release.Namespace }}
{{- end -}}
{{- end -}}

{{- define "vulntracker.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{ default (include "vulntracker.name" .) .Values.serviceAccount.name }}
{{- else -}}
{{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{- define "vulntracker.labels" -}}
app.kubernetes.io/part-of: vulntracker
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "vulntracker.api.labels" -}}
app.kubernetes.io/name: vulntracker-api
app.kubernetes.io/component: api
{{ include "vulntracker.labels" . }}
{{- end -}}
