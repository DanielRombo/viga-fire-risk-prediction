args <- commandArgs(trailingOnly=TRUE)
pasta <- paste0('/evidencias/',args[1])
for (ficheiro in c('ffmcCalc.R','dmcCalc.R','dcCalc.R','ISIcalc.r','buiCalc.R','fwiCalc.R','fwi.r')) {
 source(paste0('/workspace/experiments/xclim_062/referencia_1_8_17/',ficheiro))
}
options(digits=17)
for (entrada in list.files(pasta,pattern='_amostra_inputs.csv$',full.names=TRUE)) {
 dados <- read.csv(entrada)
 resultados <- lapply(seq_len(nrow(dados)),function(i) {
  d <- dados[i,]
  r <- fwi(d,init=data.frame(ffmc=d$ffmc0,dmc=d$dmc0,dc=d$dc0,lat=d$lat),batch=TRUE,lat.adjust=TRUE)
  data.frame(indice=d$indice,r[,c('FFMC','DMC','DC','ISI','BUI','FWI')])
 })
 write.csv(do.call(rbind,resultados),sub('_amostra_inputs.csv$','_referencia.csv',entrada),row.names=FALSE)
}
