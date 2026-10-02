# Executa o código oficial, sem o traduzir ou alterar as equações.
setwd('/prova')
for (nome in c('fine_fuel_moisture_code', 'duff_moisture_code', 'drought_code',
               'initial_spread_index', 'buildup_index', 'fire_weather_index', 'fwi')) {
  source(paste0('referencia/', nome, '.r'))
}
options(digits = 17)
dados <- read.table('referencia/test_fwi.csv', header = TRUE, sep = ';')
dir.create('resultados', showWarnings = FALSE)
write.csv(fwi(dados, init = data.frame(ffmc = 85, dmc = 6, dc = 15, lat = 40),
              lat.adjust = TRUE, batch = TRUE), 'resultados/cffdrs_completo.csv', row.names = FALSE)
for (latitude in c(38.7223, 32.6669, 37.7412)) {
  dados$lat <- latitude
  write.csv(fwi(dados, init = data.frame(ffmc = 85, dmc = 6, dc = 15, lat = latitude),
                lat.adjust = TRUE, batch = TRUE),
            paste0('resultados/cffdrs_', latitude, '.csv'), row.names = FALSE)
}
cat('Referência cffdrs calculada em R:', R.version.string, '\n')

classico <- new.env()
for (nome in c('ffmcCalc.R','dmcCalc.R','dcCalc.R','ISIcalc.r','buiCalc.R','fwiCalc.R','fwi.r')) {
  sys.source(paste0('referencia_1_8_17/', nome), envir = classico)
}
dados <- read.table('referencia/test_fwi.csv', header = TRUE, sep = ';')
for (latitude in c(40,38.7223,32.6669,37.7412)) {
  dados$lat <- latitude
  write.csv(classico$fwi(dados, init = data.frame(ffmc = 85,dmc = 6,dc = 15,lat = latitude),
                        lat.adjust = TRUE,batch = TRUE),
            paste0('resultados/cffdrs_classico_',latitude,'.csv'),row.names = FALSE)
}
cat('Referência clássica cffdrs 1.8.17 calculada sem alterações.\n')
