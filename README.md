# Sistem Lingvistic Inteligent pentru Gramatica Limbii Române [diploma-project]

Intelligent Linguistic System for the Grammar of the Romanian Language

## Authors:

* Conf. Dr. Ing. Rebedea Traian-Eugen (Scientific coordinator)
* Ing. Coteț Teodor-Mihai (Special thanks - Co-tutor)
* Nițu Ioan-Florin-Cătălin 342C4

## Sinopsis

Domeniul prelucrării limbajului natural nu este la fel de puternic dezvoltat pentru limba română așa cum este pentru altele, cum este limba engleză. Faptul de a scrie corect texte a fost mereu o necesitate, iar dezvoltarea unor instrumente care să fie de folos în această nevoie este critică. Sistemul de corectare propus primește o propoziție cu greșeli gramaticale și o corectează, folosind tehnologii de ultimă oră pentru a realiza această operație cum sunt modelele neurale bazate pe atenție ca Transformatoarele cu Codificator-Decodificator. Acestea sunt o piatră de temelie în dezvoltarea de instrumente inteligente pentru prelucrări – traducerea, rezumarea sau corectarea – de texte și sunt fundația pentru proiectul de față. Lucrarea folosește RONACC, primul corpus pentru corecții gramaticale în română pentru modelarea, antrenarea, testarea și validarea proiectului. Folosind un set de date foarte mare cu peste un milion de exemple de învățare a fost obținut un scor BLEU mediu de 45.29 de puncte, într-un timp de antrenare destul de scurt (numai două ore pentru cinci epoci) executat pe mai multe GPU-uri. Totuși, chiar și un set de date redus, de numai cincizeci de mii de exemple cu un număr de o sută de epoci obține un scor BLEU mediu de 33.29 de puncte în trei ore. **Cuvinte cheie**: limba română, gramatică, transformatoare, atenție, codificare pozițională.

## Abstract

The field of natural language processing is not as strongly developed for the Romanian language as it is for others, as is the English language. Writing texts correctly has always been a necessity, and the development of tools that will be useful in this need is critical. The proposed correction system receives a sentence with grammatical errors and corrects it, using state-of-the-art technologies to perform this operation such as attention-based neural models like Encoder-Decoder Transformers. These are a cornerstone in the development of intelligent tools for processing – translating, summarizing, or proofreading – texts and are the foundation for this project. The paper uses RONACC, the first corpus for grammatical corrections in Romanian for modeling, training, testing, and validating the project. Using a very large data set with over a million learning examples, an average BLEU score of 45.29 points was obtained, in a rather short training time (only two hours for five epochs) executed on several GPUs. However, even a small data set of only fifty thousand examples with as many as one hundred epochs achieves an average BLEU score of 33.29 points in three hours. **Keywords**: Romanian language, grammar, transformers, attention, positional encoding.
