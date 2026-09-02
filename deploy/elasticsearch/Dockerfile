# Elasticsearch 9.4.2 + IK 中文分词插件(全文检索必需)
# 若官方源拉不动, 把 FROM 换成可用代理(如 docker.1ms.run 对应路径)
FROM docker.elastic.co/elasticsearch/elasticsearch:9.4.2

# IK 版本必须和 ES 大版本一致; 若 404 到 https://release.infinilabs.com/analysis-ik/stable/ 查对应版本
RUN bin/elasticsearch-plugin install --batch https://get.infini.cloud/elasticsearch/analysis-ik/9.4.2
