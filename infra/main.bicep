@description('Azure location for all resources.')
param location string = resourceGroup().location

@description('Name of the Linux App Service Plan for the backend.')
param appServicePlanName string

@description('Name of the backend App Service.')
param backendAppName string

@description('Name of the Static Web App for the React frontend.')
param staticWebAppName string

@description('SKU name for the Static Web App (Free or Standard).')
param staticWebAppSkuName string = 'Free'

@description('SKU tier for the Static Web App (Free or Standard).')
param staticWebAppSkuTier string = 'Free'

@description('The PostgreSQL Flexible Server name hosting the existing database.')
param postgresServerName string

@secure()
@description('Full database connection string for the backend.')
param databaseUrl string

@secure()
@description('A strong JWT secret for backend authentication.')
param jwtSecretKey string

@secure()
@description('Football Data API token for external data refresh calls.')
param footballDataApiToken string

@description('Comma-separated allowed CORS origins for the backend, such as https://<your-static-webapp-hostname>')
param allowedOrigins string

@description('App location inside the repository for the frontend build.')
param staticWebAppAppLocation string = 'frontend'

@description('API location for the Static Web App. This app has no integrated Azure Functions API.')
param staticWebAppApiLocation string = ''

@description('Build output location for the frontend.')
param staticWebAppOutputLocation string = 'frontend/dist'

@description('App Service SKU for the backend plan.')
param appServiceSkuName string = 'B1'

@description('App Service SKU tier for the backend plan.')
param appServiceSkuTier string = 'Basic'

@description('Number of instances for the backend App Service Plan.')
param appServiceSkuCapacity int = 1

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2022-12-01' existing = {
  name: postgresServerName
}

resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: appServiceSkuName
    tier: appServiceSkuTier
    capacity: appServiceSkuCapacity
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${backendAppName}-ai'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}

resource backendApp 'Microsoft.Web/sites@2022-03-01' = {
  name: backendAppName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      appCommandLine: 'python -m uvicorn app.api.main:app --app-dir src --host 0.0.0.0 --port 8000'
      alwaysOn: true
      http20Enabled: true
      healthCheckPath: '/api/health'
      ftpsState: 'Disabled'
      appSettings: [
        {
          name: 'DATABASE_URL'
          value: databaseUrl
        }
        {
          name: 'JWT_SECRET_KEY'
          value: jwtSecretKey
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'FOOTBALL_DATA_API_TOKEN'
          value: footballDataApiToken
        }
        {
          name: 'ALLOWED_ORIGINS'
          value: allowedOrigins
        }
        {
          name: 'AUTO_CREATE_TABLES'
          value: '1'
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
      ]
    }
    httpsOnly: true
  }
  dependsOn: [
    appServicePlan
    appInsights
  ]
}

resource staticWebApp 'Microsoft.Web/staticSites@2023-08-01' = {
  name: staticWebAppName
  location: location
  sku: {
    name: staticWebAppSkuName
    tier: staticWebAppSkuTier
  }
  properties: {
    buildProperties: {
      appLocation: staticWebAppAppLocation
      apiLocation: staticWebAppApiLocation
      outputLocation: staticWebAppOutputLocation
    }
  }
}

output backendAppUrl string = 'https://${backendApp.properties.defaultHostName}'
output staticWebAppUrl string = 'https://${staticWebApp.properties.defaultHostname}'
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
