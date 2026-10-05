# Apenas diagnóstico: funções originais com RH=100, sem o pré-processamento
# da função pública fwi(). NÃO substitui o resultado de referência reprovado.
for (ficheiro in c('ffmcCalc.R','dmcCalc.R','dcCalc.R','ISIcalc.r','buiCalc.R','fwiCalc.R','fwi.r')) {
 source(paste0('/workspace/experiments/xclim_062/referencia_1_8_17/',ficheiro))
}
options(digits=17)
linhas <- list()
for (entrada in list.files('/evidencias/365',pattern='_amostra_inputs.csv$',full.names=TRUE)) {
 dados <- read.csv(entrada)
 for (i in which(dados$rh==100)) {
  d <- dados[i,]
  ffmc <- .ffmcCalc(d$ffmc0,d$temp,d$rh,d$ws,d$prec)
  dmc <- .dmcCalc(d$dmc0,d$temp,d$rh,d$prec,d$lat,d$mon,TRUE)
  dc <- .dcCalc(d$dc0,d$temp,d$rh,d$prec,d$lat,d$mon,TRUE)
  isi <- .ISIcalc(ffmc,d$ws,FALSE)
  bui <- .buiCalc(dmc,dc)
  fwi <- .fwiCalc(isi,bui)
  linhas[[length(linhas)+1]] <- data.frame(regiao=sub('_amostra_inputs.csv$','',basename(entrada)),
    indice=d$indice,FFMC=ffmc,DMC=dmc,DC=dc,ISI=isi,BUI=bui,FWI=fwi)
 }
}
write.csv(do.call(rbind,linhas),'/evidencias/diagnostico_rh100.csv',row.names=FALSE)
