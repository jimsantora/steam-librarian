{{/*
Expand the name of the chart.
*/}}
{{- define "steam-librarian.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "steam-librarian.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "steam-librarian.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "steam-librarian.labels" -}}
helm.sh/chart: {{ include "steam-librarian.chart" . }}
{{ include "steam-librarian.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "steam-librarian.selectorLabels" -}}
app.kubernetes.io/name: {{ include "steam-librarian.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "steam-librarian.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "steam-librarian.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Steam secret name
*/}}
{{- define "steam-librarian.secretName" -}}
{{- if .Values.steam.existingSecret }}
{{- .Values.steam.existingSecret }}
{{- else }}
{{- include "steam-librarian.fullname" . }}-steam-secret
{{- end }}
{{- end }}

{{/*
PVC name
*/}}
{{- define "steam-librarian.pvcName" -}}
{{- if .Values.persistence.existingClaim }}
{{- .Values.persistence.existingClaim }}
{{- else }}
{{- include "steam-librarian.fullname" . }}-data
{{- end }}
{{- end }}